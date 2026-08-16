import { TestBed } from '@angular/core/testing';
import { configureTestBed } from '@testing';

import { WikiService } from './wiki.service';

describe('WikiService', () => {
  let service: WikiService;

  beforeEach(() => {
    configureTestBed();
    TestBed.configureTestingModule({});
    service = TestBed.inject(WikiService);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });
});
