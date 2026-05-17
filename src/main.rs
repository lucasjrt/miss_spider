use std::env;
use std::io::{self, IsTerminal, Read};

mod spider;
mod tor;
mod url;

use spider::crawl;

type Error = Box<dyn std::error::Error + Send + Sync>;

#[tokio::main]
async fn main() {
    let sites = parse_sites();
    eprintln!("Scraping sites: {:?}", sites);
    for site in sites {
        eprintln!("Scraping {}", site);
        match crawl(&site).await {
            Ok(links) => {
                for link in links {
                    println!("{}", link);
                }
            }
            Err(e) => {
                eprintln!("Error scraping {}: {}", site, e);
            }
        }
    }
}

fn parse_sites() -> Vec<String> {
    let args: Vec<String> = env::args().collect();
    let piped_input = read_piped_input();
    let sites = collect_sites(&args, piped_input.as_deref());

    if sites.is_empty() {
        print_usage(&args);
    }

    sites
}

fn read_piped_input() -> Option<String> {
    if io::stdin().is_terminal() {
        return None;
    }

    let mut sites = String::new();
    io::stdin()
        .read_to_string(&mut sites)
        .expect("Failed to read from stdin");
    Some(sites)
}

fn collect_sites(args: &[String], input: Option<&str>) -> Vec<String> {
    let mut sites = Vec::new();

    if let Some(input) = input {
        sites.extend(input.split_whitespace().map(String::from));
    }

    sites.extend(args.iter().skip(1).cloned());
    sites
}

fn print_usage(args: &[String]) {
    if let Some(program_name) = args.first() {
        eprintln!("Usage: {} <url>", program_name);
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn collects_args_without_input() {
        let args = vec![
            "miss_spider".to_string(),
            "http://first.onion".to_string(),
            "http://second.onion".to_string(),
        ];

        let sites = collect_sites(&args, None);

        assert_eq!(
            sites,
            vec![
                "http://first.onion".to_string(),
                "http://second.onion".to_string()
            ]
        );
    }

    #[test]
    fn combines_piped_input_and_args() {
        let args = vec!["miss_spider".to_string(), "http://arg.onion".to_string()];

        let sites = collect_sites(
            &args,
            Some("http://stdin-one.onion\nhttp://stdin-two.onion"),
        );

        assert_eq!(
            sites,
            vec![
                "http://stdin-one.onion".to_string(),
                "http://stdin-two.onion".to_string(),
                "http://arg.onion".to_string()
            ]
        );
    }

    #[test]
    fn collects_input_without_args() {
        let args = vec!["miss_spider".to_string()];

        let sites = collect_sites(&args, Some("http://stdin-one.onion"));

        assert_eq!(sites, vec!["http://stdin-one.onion".to_string()]);
    }

    #[test]
    fn returns_empty_when_no_sites_are_provided() {
        let args = vec!["miss_spider".to_string()];
        let sites = collect_sites(&args, None);

        assert!(sites.is_empty());
    }
}
