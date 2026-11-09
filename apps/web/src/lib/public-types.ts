/** Mirrors shift_api.public_routes response models. */
export type PublicContract = {
  id: string;
  title: string;
  company: string;
  trade: string;
  city: string;
  start_date: string;
  end_date: string;
  pay_rate_cents: number;
  pay_unit: 'hour' | 'day' | 'fixed';
  posting_type: 'individual' | 'agency';
};
export type PublicContracts = { demo: boolean; contracts: PublicContract[] };
