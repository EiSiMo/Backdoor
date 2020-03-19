use std::process::Command;
use std::error::Error;
use std::str::from_utf8;

#[cfg(not(target_os = "windows"))]
#[cfg(not(target_os = "linux"))]
pub fn execute_command(args: &Vec<&str>) -> (&str, &str) {
    Error("unsupported platform")
}

#[cfg(target_os = "windows")]
pub fn execute_command(command: &str) -> (str, str) {
    Ok(Command::new("cmd")
        .arg("/C")
        .arg(command)
        .output()?)
}

#[cfg(target_os = "linux")]
pub fn execute_command(command: &str) -> Result<String, Box<dyn Error>> {
    let output = Command::new("sh")
        .arg("-c")
        .arg(command)
        .output()?;
    let stdout_decoded = from_utf8(&output.stdout)?;
    let stderr_decoded = from_utf8(&output.stderr)?;
    let out = stdout_decoded.to_owned() + stderr_decoded;
    Ok(out)
}
