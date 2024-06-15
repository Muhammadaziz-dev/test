import { UserType } from "@/types/user.type";
import { ProductType } from "@/types/product.type";

export interface OrderType {
  id: number;
  name: string;
  phone_number: string;
  owner: UserType;
  date: string;
  shop: number;
  total_price: string;
  total_amount: string;
  products: {
    id: number;
    product: number;
    price: string;
    quantity: number;
    order: number;
    product_data: ProductType;
  }[];
}

export interface CreateOrderType {
  name: string;
  phone_number: string;
  products:
    | {
        product: string;
        price: string;
        quantity: string;
      }[]
    | any;
  shop: number;
}
