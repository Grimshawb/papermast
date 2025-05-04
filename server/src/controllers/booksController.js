const booksService = require('../services/booksService');

exports.searchBooks = async (req, res) => {
  const { q } = req.query;
  try {
    const data = await booksService.fetchBooks(q);
    res.json(data);
  } catch (err) { console.log(err);
    res.status(500).json({ error: 'There was a problem searching books' });
  }
};

exports.popularFiction = async (req, res) => {
  try {
    const data = await booksService.popularFiction();
    res.json(data);
  } catch (err) { console.log(err);
    res.status(400).json({ error: 'Error searching popular fiction' });
  }
}
