import { locationApi } from '../api/client';

const COUNTRY_CODE_KEY = 'approximate_country_code';

export function getCountryCode(): string | null {
  return localStorage.getItem(COUNTRY_CODE_KEY);
}

export async function detectCountryFromIp(): Promise<string> {
  const data = await locationApi.estimateCountry();
  const countryCode = data.country_code;
  if (typeof countryCode !== 'string' || !/^[A-Z]{2}$/i.test(countryCode)) {
    throw new Error('Country lookup returned no valid country code');
  }

  return countryCode.toUpperCase();
}

export function confirmCountryCode(countryCode: string): void {
  localStorage.setItem(COUNTRY_CODE_KEY, countryCode);
}

export function clearCountryCode(): void {
  localStorage.removeItem(COUNTRY_CODE_KEY);
}
