use std::env;
use std::io;

use atty::Stream;

fn main() {
    let stdin = io::stdin();
    let mut args: Vec<String> = env::args().collect();
    if atty::is(Stream::Stdin) {
        let program_name = args.remove(0);
        for arg in args.iter() {
            println!("Scraping: {}", arg);
        }
        if args.is_empty() {
            println!("Usage: {} <url>", program_name);
        }
    } else {
        let mut sites = String::new();
        match stdin.read_line(&mut sites) {
            Ok(_) => {}
            Err(e) => {
                eprintln!("Error: Could not read piped input: {}", e);
                panic!();
            }
        }
        let mut sites: Vec<&str> = sites.split_whitespace().collect();
        if !args.is_empty() {
            sites.extend(args[1..].iter().map(|s| s.as_str()));
        }
        for site in sites {
            println!("Scraping: {}", site);
        }
    }
}
