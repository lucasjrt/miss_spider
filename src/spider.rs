use std::collections::HashSet;
use std::sync::LazyLock;

use crate::tor::{tor_client_from_env, tor_request_with_client};
use crate::url::ensure_http_scheme;
use regex::Regex;

use crate::Error;

const ONION_LINK_PATTERN: &str = r#"((?:https?://)?([^\.'">]+\.onion)([^\s'"<;]*))"#;
static ONION_LINK_REGEX: LazyLock<Regex> =
    LazyLock::new(|| Regex::new(ONION_LINK_PATTERN).expect("valid onion link regex"));

struct Spider {
    tor_client: reqwest::Client,
    to_visit: Vec<String>,
    queued: HashSet<String>,
    visited_set: HashSet<String>,
    visited: Vec<String>,
}

pub async fn crawl(address: &str) -> Result<Vec<String>, Error> {
    let mut spider = Spider::new()?;
    spider.crawl(address).await
}

impl Spider {
    pub fn new() -> Result<Self, Error> {
        Ok(Self::with_client(tor_client_from_env()?))
    }

    fn with_client(tor_client: reqwest::Client) -> Self {
        Self {
            tor_client,
            to_visit: Vec::new(),
            queued: HashSet::new(),
            visited_set: HashSet::new(),
            visited: Vec::new(),
        }
    }

    pub async fn crawl(&mut self, address: &str) -> Result<Vec<String>, Error> {
        self.queue(address.to_string());
        while !self.to_visit.is_empty() {
            self.crawl_next().await?;
        }
        Ok(self.visited.clone())
    }

    pub async fn crawl_next(&mut self) -> Result<(), Error> {
        let Some(next) = self.to_visit.pop() else {
            return Ok(());
        };

        self.queued.remove(&next);
        if self.visited_set.contains(&next) {
            return Ok(());
        }

        let response = tor_request_with_client(&next, &self.tor_client).await?;
        let body = response.text().await?;

        self.visited_set.insert(next.clone());
        self.visited.push(next.clone());

        let count = self.scrape(&body);
        eprintln!("Scraped {} links from {}", count, next);
        Ok(())
    }

    pub fn scrape(&mut self, content: &str) -> usize {
        let mut count = 0;
        for cap in ONION_LINK_REGEX.captures_iter(content) {
            let capture = ensure_http_scheme(&cap[1]);
            if self.queue(capture) {
                count += 1;
            }
        }
        count
    }

    fn queue(&mut self, address: String) -> bool {
        if self.visited_set.contains(&address) || !self.queued.insert(address.clone()) {
            return false;
        }

        self.to_visit.push(address);
        true
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn scrape_queues_unique_normalized_onion_links() {
        let client = reqwest::Client::new();
        let mut spider = Spider::with_client(client);

        let count = spider.scrape(
            r#"
            <a href="firstaaaaaaaaaaaaaaaaaaaaaaaaaaaa.onion/path">first</a>
            <a href="http://firstaaaaaaaaaaaaaaaaaaaaaaaaaaaa.onion/path">duplicate</a>
            <a href="https://seconddddddddddddddddddddddddddd.onion">second</a>
            "#,
        );

        assert_eq!(count, 2);
        assert_eq!(
            spider.to_visit,
            vec![
                "http://firstaaaaaaaaaaaaaaaaaaaaaaaaaaaa.onion/path",
                "https://seconddddddddddddddddddddddddddd.onion"
            ]
        );
    }

    #[test]
    fn queue_ignores_already_visited_urls() {
        let client = reqwest::Client::new();
        let mut spider = Spider::with_client(client);

        spider
            .visited_set
            .insert("http://visited.onion".to_string());

        assert!(!spider.queue("http://visited.onion".to_string()));
        assert!(spider.to_visit.is_empty());
    }
}
