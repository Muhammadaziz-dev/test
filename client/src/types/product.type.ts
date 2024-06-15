export interface ProductType {
  id: number;
  name: string;
  enter_price: string;
  out_price: string;
  date_added: string;
  in_stock: boolean;
  currency: string;
  owner: number;
  count: number;
  info: string;
  properties: {
    id: number;
    product: number;
    feature: string;
    value: string;
  }[];
  category: {
    id: number;
    name: string;
    category_slug: string;
  };
  shop: number;
  images: {
    id: number;
    product: number;
    image: string;
    image_url: string;
  }[];
}
