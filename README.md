# Miss Spider

Miss Spider is a Dark Net indexer that takes one or more URLs as input and scrapes the content of the page to extract links to other pages. It then follows these links and repeats the process until it has no more links to follow. The result is a list of URLs that can be used to find hidden services. It can also be used to extract regex patterns from the pages it visits, in case you are looking for something specific.

## Installation

This project doesn't provide a binary, so you will need to compile it with `cargo`. If you don't have `cargo` installed, you can get it from this [link](https://rustup.rs/).

Once you have `cargo` installed, you can compile the project with the following command:

```bash
cargo build --release
```

The binary will be located at `target/release/miss_spider`.

## Tor setup

Miss Spider uses Tor to access the Dark Net. You will need to have Tor installed and running on your machine. If you don't have it installed, you can get it from this [link](https://www.torproject.org/download/tor/).

Once you have Tor installed, you will need to configure it to use a control port. You can do this by adding the following lines to your `torrc` file (usually located at `/etc/tor/torrc`):

```
ControlPort 9051 # Make sure to search and uncomment this line
HashedControlPassword 16:XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX # Make sure to replace the Xs with the hashed password
```

To generate the hashed password, you can use the following command:

```bash
tor --hash-password PASSWORD
```

## Usage

You need to set the variable TOR_PROXY_PASSWORD with the password you hashed in the previous step. You can do this by running the following command:

```bash
export TOR_PROXY_PASSWORD=PASSWORD
```

> Replace PASSWORD with the non-hashed password you generated in the previous step.

If you want to set a different tor proxy than localhost, you can set the variable TOR_PROXY_ADDRESS with the address of the tor proxy. **You must set either TOR_PROXY_ADDRESS or TOR_PROXY_PASSWORD to use Miss Spider**.

The following command will start Miss Spider and use the given URL as the starting point:

```bash
miss_spider http://example.com http://example2.com
```

Also it supports piping, this allows you to read from files:

```bash
cat urls.txt | miss_spider
```
