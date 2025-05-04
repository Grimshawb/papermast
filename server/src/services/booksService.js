const axios = require('axios');

exports.fetchBooks = async (query) => {
  const apiKey = process.env.GOOGLE_BOOKS_API_KEY;
  const url = `https://www.googleapis.com/books/v1/volumes`;

  const response = await axios.get(url, {
    params: {
      q: query,
      key: apiKey
    }
  });

  return response.data;
};

exports.popularFiction = async () => {
  const apiKey = process.env.GOOGLE_BOOKS_API_KEY;
  const startIndex = 0;
  const maxResults = 40;
  //this.http.get<any>(`${this.apiUrl}?q=subject:fiction&orderBy=relevance&startIndex=${index}&maxResults=40&key=${this.apiKey}`)
  const url = `https://www.googleapis.com/books/v1/volumes`;

  const response = await axios.get(url, {
    params: {
      q: `subject:fiction`,
      orderBy: 'relevance',
      startIndex: startIndex,
      maxResults: maxResults,
      key: apiKey 
    }
    
  });
  
  return response.data;
};
