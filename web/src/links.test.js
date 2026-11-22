import { expect, it } from 'vitest';
import { nobrokerSearchUrl } from './links.js';

it('builds a NoBroker search centred on the society', () => {
  const url = new URL(nobrokerSearchUrl({ name: 'Ittina Mahavir', lat: 12.8402, lng: 77.6482 }, 'bangalore'));
  expect(url.origin + url.pathname).toBe('https://www.nobroker.in/property/rent/bangalore/Ittina%20Mahavir');
  expect(url.searchParams.get('radius')).toBe('1.0');
  expect(JSON.parse(atob(url.searchParams.get('searchParam')))).toEqual([{ lat: 12.8402, lon: 77.6482, placeId: '', placeName: 'Ittina Mahavir' }]);
});

it('copes with names outside Latin-1', () => {
  const url = new URL(nobrokerSearchUrl({ name: 'Shree Ganesh – Nest', lat: 1, lng: 2 }, 'bangalore'));
  const bytes = Uint8Array.from(atob(url.searchParams.get('searchParam')), (c) => c.charCodeAt(0));
  expect(JSON.parse(new TextDecoder().decode(bytes))[0].placeName).toBe('Shree Ganesh – Nest');
});
