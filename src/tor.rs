use crate::Error;

pub async fn tor_request(address: &str) -> Result<reqwest::Response, Error> {
    let proxy_password = std::env::var("TOR_PROXY_PASSWORD").unwrap_or("".to_string());
    let proxy_address = std::env::var("TOR_PROXY_ADDRESS").unwrap_or_else(|_| {
        if proxy_password.is_empty() {
            panic!("TOR_PROXY_PASSWORD must be set if TOR_PROXY_ADDRESS is not set");
        }
        format!("socks5h://username:{}@127.0.0.1:9050", proxy_password).to_string()
    });
    let proxy = reqwest::Proxy::all(proxy_address)?;
    let client = reqwest::Client::builder().proxy(proxy).build()?;
    tor_request_with_client(address, &client).await
}

pub async fn tor_request_with_client(
    address: &str,
    client: &reqwest::Client,
) -> Result<reqwest::Response, Error> {
    let address = if address.starts_with("http") {
        address.to_string()
    } else {
        format!("http://{}", address)
    };
    let response = client.get(address).send().await?;
    Ok(response)
}
