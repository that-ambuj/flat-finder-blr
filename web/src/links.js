export function nobrokerSearchUrl(s, city) {
  const place = [{ lat: s.lat, lon: s.lng, placeId: '', placeName: s.name }];
  // btoa() accepts Latin-1 only. Encode as UTF-8 bytes first.
  const param = btoa(String.fromCharCode(...new TextEncoder().encode(JSON.stringify(place))));
  return `https://www.nobroker.in/property/rent/${encodeURIComponent(city)}/${encodeURIComponent(s.name)}?searchParam=${encodeURIComponent(param)}&radius=1.0`;
}
