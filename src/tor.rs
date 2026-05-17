use crate::{url::ensure_http_scheme, Error};

const DEFAULT_TOR_PROXY_PREFIX: &str = "socks5h://username:";
const DEFAULT_TOR_PROXY_SUFFIX: &str = "@127.0.0.1:9050";
const TOR_PROXY_ADDRESS_ENV: &str = "TOR_PROXY_ADDRESS";
const TOR_PROXY_PASSWORD_ENV: &str = "TOR_PROXY_PASSWORD";

pub fn tor_client_from_env() -> Result<reqwest::Client, Error> {
    let proxy_address = tor_proxy_address_from_env()?;
    let proxy = reqwest::Proxy::all(proxy_address)?;
    Ok(reqwest::Client::builder().proxy(proxy).build()?)
}

pub async fn tor_request_with_client(
    address: &str,
    client: &reqwest::Client,
) -> Result<reqwest::Response, Error> {
    Ok(client
        .get(ensure_http_scheme(address))
        .send()
        .await?
        .error_for_status()?)
}

fn tor_proxy_address_from_env() -> Result<String, Error> {
    if let Ok(proxy_address) = std::env::var(TOR_PROXY_ADDRESS_ENV) {
        if proxy_address.is_empty() {
            return Err(std::io::Error::new(
                std::io::ErrorKind::InvalidInput,
                format!("{TOR_PROXY_ADDRESS_ENV} must not be empty"),
            )
            .into());
        }

        return Ok(proxy_address);
    }

    let proxy_password = std::env::var(TOR_PROXY_PASSWORD_ENV).map_err(|_| {
        std::io::Error::new(
            std::io::ErrorKind::InvalidInput,
            format!("{TOR_PROXY_PASSWORD_ENV} must be set if {TOR_PROXY_ADDRESS_ENV} is not set"),
        )
    })?;

    if proxy_password.is_empty() {
        return Err(std::io::Error::new(
            std::io::ErrorKind::InvalidInput,
            format!(
                "{TOR_PROXY_PASSWORD_ENV} must not be empty if {TOR_PROXY_ADDRESS_ENV} is not set"
            ),
        )
        .into());
    }

    Ok(format!(
        "{DEFAULT_TOR_PROXY_PREFIX}{proxy_password}{DEFAULT_TOR_PROXY_SUFFIX}"
    ))
}
