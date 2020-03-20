use json::JsonValue;
use std::error::Error;
use std::str::from_utf8;

pub fn bytes2json(data: &Vec<u8>) -> Result<json::JsonValue, Box<dyn Error>> {
    let data_decoded: &str = from_utf8(&data)?;
    let data_json: json::JsonValue = json::parse(&data_decoded)?;
    Ok(data_json)
}

//pub fn json2bytes(data: json::JsonValue) -> Result<Vec<u8>, Box<dyn Error>> {

//}

pub fn jsonval2str(val: &JsonValue) -> &str {
    match val.as_str() {
        Some(val_str) => {
            val_str
        },
        None => {
            ""
        }
    }
}