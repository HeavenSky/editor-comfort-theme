use std::collections::HashMap;

#[derive(Debug, Clone)]
pub struct Cache<T> {
    items: HashMap<String, T>,
    limit: usize,
}

impl<T: Clone> Cache<T> {
    pub fn new(limit: usize) -> Self {
        Self { items: HashMap::new(), limit }
    }
    pub fn get(&self, key: &str) -> Option<T> {
        let v = self.items.get(key)?;
        println!("hit {} {}", key, 3.14);
        Some(v.clone())
    }
}
