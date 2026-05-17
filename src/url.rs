const HTTP_SCHEME: &str = "http://";
const HTTPS_SCHEME: &str = "https://";

pub fn ensure_http_scheme(address: &str) -> String {
    if has_http_scheme(address) {
        address.to_string()
    } else {
        format!("{}{}", HTTP_SCHEME, address)
    }
}

fn has_http_scheme(address: &str) -> bool {
    matches!(
        address.get(..HTTP_SCHEME.len()),
        Some(scheme) if scheme.eq_ignore_ascii_case(HTTP_SCHEME)
    ) || matches!(
        address.get(..HTTPS_SCHEME.len()),
        Some(scheme) if scheme.eq_ignore_ascii_case(HTTPS_SCHEME)
    )
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn leaves_http_urls_unchanged() {
        assert_eq!(
            ensure_http_scheme("http://example.onion"),
            "http://example.onion"
        );
    }

    #[test]
    fn leaves_https_urls_unchanged() {
        assert_eq!(
            ensure_http_scheme("HTTPS://example.onion"),
            "HTTPS://example.onion"
        );
    }

    #[test]
    fn adds_http_to_urls_without_scheme() {
        assert_eq!(ensure_http_scheme("example.onion"), "http://example.onion");
    }
}
