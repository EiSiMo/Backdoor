use std::time;

// time to wait before retry when connecting to server fails
pub const REFUSED_SLEEP_TIME: time::Duration = time::Duration::from_secs(30);
// ip address of the server
pub const ADDRESS: &str = "127.0.0.1";
// port to connect to at the server
pub const PORT: u16 = 10001;
// size of the header packet
pub const HEADER_LENGTH: usize = 1024;
// msg to send the server to indicate heacer received
pub const ACK: &[u8] =  "ACK".as_bytes();
