export interface UserType {
  first_name: string;
  last_name: string;
  id: number;
  status: {
    status_name: string;
    price: number;
    id: number;
  } | null;
  phone_number: string;
  profile_image: string | null;
  last_login: string;
}

export interface TokenType {
  token: string;
}
