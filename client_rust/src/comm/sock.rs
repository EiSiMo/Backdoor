use std::net::{TcpStream, Shutdown};
use std::io::{Read, Write};
use std::error::Error;
use std::thread;
use json;
use crate::comm::constants;
use crate::comm::crypt;
use crate::comm::serialize;
use std::str::from_utf8;

pub fn establish() -> TcpStream {
    loop {
        match TcpStream::connect(format!("{}:{}", constants::ADDRESS, constants::PORT.to_string())) {
            Ok(stream) => {
                println!("successfully connected!");
                return stream;
            },
            Err(error) => {
                println!("{}", error);
                thread::sleep(constants::REFUSED_SLEEP_TIME);
            }
        }
    }
}

pub fn close(stream: &mut TcpStream) {
    match stream.shutdown(Shutdown::Both) {
        Ok(()) => {}
        Err(error) => {
            println!("{}", error);
        }
    }
}

pub fn recv(stream: &mut TcpStream) -> Result<json::JsonValue, Box<dyn Error>> {
    let mut buffer: Vec<u8> = vec![0 as u8; constants::HEADER_LENGTH];
    stream.read(&mut buffer)?;
    let header: &str = from_utf8(&buffer)?;
    let header_trimmed: &str = header.trim_matches(char::from(0));
    let data_length: usize = header_trimmed.parse::<usize>()?;
    stream.write_all(constants::ACK)?;
    let mut data: Vec<u8> = vec![0 as u8; data_length];
    stream.read_exact(&mut data)?;
    let data_decrypted = crypt::decrypt(&data)?;
    let data_serialized = serialize::bytes2json(&data_decrypted)?;
    Ok(data_serialized)
}

pub fn send(steam: TcpStream, data: Vec<u8>) -> Result<(), Box<dyn Error>>{
    Ok(())
}
