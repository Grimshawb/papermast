const express = require('express');
const router = express.Router();
const booksController = require('../controllers/booksController');

router.get('/search', booksController.searchBooks);
router.get('/pop-fiction', booksController.popularFiction);

module.exports = router;
