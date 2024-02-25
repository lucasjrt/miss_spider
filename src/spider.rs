use crate::tor::tor_request_with_client;
use regex::Regex;

use crate::Error;

struct Spider {
    tor_client: reqwest::Client,
    to_visit: Vec<String>,
    visited: Vec<String>,
}

impl Spider {
    pub fn new() -> Result<Self, Error> {
        let proxy_password = std::env::var("TOR_PROXY_PASSWORD").unwrap_or("".to_string());
        let proxy_address = std::env::var("TOR_PROXY_ADDRESS").unwrap_or_else(|_| {
            if proxy_password.is_empty() {
                panic!("TOR_PROXY_PASSWORD must be set if TOR_PROXY_ADDRESS is not set");
            }
            format!("socks5h://username:{}@127.0.0.1:9050", proxy_password).to_string()
        });
        let proxy = reqwest::Proxy::all(proxy_address)?;
        let client = reqwest::Client::builder().proxy(proxy).build()?;
        Ok(Self {
            tor_client: client,
            to_visit: Vec::new(),
            visited: Vec::new(),
        })
    }

    pub async fn crawl(&mut self, address: &str) -> Result<Vec<String>, Box<Error>> {
        self.to_visit.push(address.to_string());
        while !self.to_visit.is_empty() {
            self.crawl_next().await?;
        }
        Ok(self.visited.clone())
    }

    pub async fn crawl_next(&mut self) -> Result<(), Box<Error>> {
        if let Some(next) = self.to_visit.pop() {
            let response = tor_request_with_client(&next, &self.tor_client).await?;
            let body = response
                .text()
                .await
                .map_err(|e| Box::new(e) as Box<dyn std::error::Error>)?;
            let count = self.scrape(body).await?;
            println!("Scraped {} links from {}", count, next);
        } else {
            println!("No more links to visit");
        }
        Ok(())
    }

    pub async fn scrape(&mut self, content: String) -> Result<usize, Box<Error>> {
        let re = Regex::new(r#"((?:https?://)?([^\.'">]+\.onion)([^\s'"<;]+))"#).unwrap();
        let captures = re.captures_iter(&content);
        let mut count = 0;
        for cap in captures {
            let mut capture = cap[1].to_string();
            if !capture.starts_with("http") {
                capture = format!("http://{}", capture);
            }
            if !self.visited.contains(&capture) && !self.to_visit.contains(&capture) {
                count += 1;
                self.to_visit.push(capture);
            }
        }
        Ok(count)
    }
}
