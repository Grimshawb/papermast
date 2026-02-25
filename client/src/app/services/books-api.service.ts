import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Observable, filter, map, take } from 'rxjs';
import { ApiBook } from '../models/books-api';
import { environment } from '../../environment.prod';
import { toHttpParams } from '../utils';
import { BookSearchRequestDto } from '../models';

@Injectable({
  providedIn: 'root'
})
export class BooksApiService {

  private baseUrl = `${environment.BACK_END_URL}booksapi`;

  constructor(protected http: HttpClient) { }

  // searchBooks(query: string): Observable<any> {
  //   return this.http.get(`${this.apiUrl}/search?q=${encodeURIComponent(query)}`);
  // }

  // popularFiction(): Observable<any> {
  //   const params = {
  //     q: `subject:fiction`,
  //     orderBy: 'relevance',
  //     startIndex: 0,
  //     maxResults: 40,
  //     key: this.apiKey
  //   }
  //   return this.http.get(`${this.apiUrl}/pop-fiction`);
  // }

  public apiSearch(request: BookSearchRequestDto): Observable<ApiBook[]> {

  // q - Search for volumes that contain this text string. There are special keywords you can specify in the search terms to search in particular fields, such as:
  // intitle: Returns results where the text following this keyword is found in the title.
  // inauthor: Returns results where the text following this keyword is found in the author.
  // inpublisher: Returns results where the text following this keyword is found in the publisher.
  // subject: Returns results where the text following this keyword is listed in the category list of the volume.
  // isbn: Returns results where the text following this keyword is the ISBN number.
  // lccn: Returns results where the text following this keyword is the Library of Congress Control Number.
  // oclc: Returns results where the text following this keyword is the Online Computer Library Center number.

    return this.http.get<any>(`${this.baseUrl}/search`, {params: toHttpParams(request)})
    .pipe(
      take(1),
      map((res: any) => {
        let books: ApiBook[] = [];
        for (let i = 0; i < res.items.length; i++) {
          let bookData = res.items[i].volumeInfo;
          if (bookData.language === 'en') {
            books.push(res.items[i].volumeInfo as ApiBook);
          }
        }
        return books;
      })
    );
  }
}
