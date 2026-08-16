import { TestBed } from '@angular/core/testing';
import { configureTestBed } from '@testing';

import { ToasterService } from './toaster.service';

describe('ToasterService', () => {
  let service: ToasterService;

  beforeEach(() => {
    configureTestBed();
    TestBed.configureTestingModule({});
    service = TestBed.inject(ToasterService);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });
});
