use std::env;
use std::io;

use atty::Stream;

mod spider;
mod tor;

use spider::crawl;

type Error = Box<dyn std::error::Error>;

#[tokio::main]
async fn main() {
    let sites = parse_sites();
    println!("Scraping sites: {:?}", sites);
    for site in sites {
        println!("Scraping {}", site);
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
    let stdin = io::stdin();
    let mut args: Vec<String> = env::args().collect();
    let mut sites: Vec<String> = Vec::new();
    if atty::is(Stream::Stdin) {
        let program_name = args.remove(0);
        if args.is_empty() {
            println!("Usage: {} <url>", program_name);
            return sites;
        }
        sites.extend(args.iter().map(|s| s.to_string()));
    } else {
        let mut sites = String::new();
        stdin
            .read_line(&mut sites)
            .expect("Failed to read from stdin");
        let mut sites: Vec<&str> = sites.split_whitespace().collect();
        if !args.is_empty() {
            sites.extend(args[1..].iter().map(|s| s.as_str()));
        }
    }
    sites
}
