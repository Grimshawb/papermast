const express = require('express');
const cors = require('cors');
const booksRoutes = require('./routes/booksRoutes');

const app = express();
app.use(cors()); // app.use(cors({ origin: 'https://your-frontend-domain.com' }));
app.use(express.json());

app.use('/api/books', booksRoutes);

module.exports = app;
