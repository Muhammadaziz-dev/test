import { UserType } from "@/types/user.type";
import { OrderType } from "@/types/order.type";
import { ProductType } from "@/types/product.type";

export interface ShopsType {
  id: number;
  name: string;
  logo: null | string;
  banner: null | string;
  owner: UserType;
  manager: null | number;
  manager_details: null | UserType;
  products_count: number;
  orders_count: number;
  total_orders_value: number;
}

export interface ShopDetailType {
  id: number;
  name: string;
  logo: null | string;
  banner: null | string;
  owner: UserType;
  manager: null | UserType;
  orders: OrderType[];
  products: ProductType[];
}
