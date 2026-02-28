import { ApiBookIdentifier, BestsellerList, IsbnType, NytBook, NytBuyLink } from "../models";

export function responseToBestsellerLists(obj: any): BestsellerList[] {

  if (obj?.status == 'OK') {
    const results = obj.results;
    return results.lists.filter(l => !!l).map(l => {
      return {
        bestsellersDate: results?.bestsellers_date || undefined,
        name: l?.display_name || '',
        books: l?.books?.filter(b => !!b)?.map(b => {
          return {
            ageGroup: b?.age_group || '',
            amazonProductUrl: b?.amazon_product_url || '',
            author: b?.author || '',
            bookImage: b?.book_image || '',
            buyLinks: b?.buy_links?.filter(bl => !!bl)?.map(bl => {
              return {
                name: bl?.name,
                url: bl?.url
              } as NytBuyLink
            }),
            contributor: b?.contributor || '',
            contributorNote: b?.contributor_note || '',
            createdDate: b?.created_date || undefined,
            description: b?.description || '',
            isbns: [
              {type: IsbnType.ISBN_10, identifier: b?.primary_isbn10} as ApiBookIdentifier,
              {type: IsbnType.ISBN_13, identifier: b?.primary_isbn13} as ApiBookIdentifier,
            ],
            publisher: b?.publisher || '',
            title: b?.title || '',
            weeksOnList: b?.weeks_on_list || 0
          } as NytBook
        })
      } as BestsellerList;
    })
  }
  return [];
}
