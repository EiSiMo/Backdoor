use crate::comm::sock;
use std::error::Error;

pub mod comm;

fn main() {
    let mut stream = sock::establish();
    loop {
        match sock::recv(&mut stream) {
            Ok(request) => {
                println!("received: {:?}", request);
            },
            Err(error) => {
                println!("error: {}", error);
                break
            }
        }
    }
    
    sock::close(&mut stream);
    println!("Terminated.");
}
