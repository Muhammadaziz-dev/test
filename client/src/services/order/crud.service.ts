import { CreateOrderType } from "@/types/order.type";
import axios from "axios";
import { getCookie } from "@/lib/cookie";

const token = getCookie("token");

export const OrderCrudService = {
  async create(data: CreateOrderType) {
    try {
      const { status } = await axios.post(
        `${process.env.API}/orders/create/`,
        data,
        {
          headers: {
            "Content-Type": "application/json",
            Authorization: `Token ${token}`,
          },
        },
      );

      if (status == 201) {
        return status;
      }
    } catch (error: any) {
      console.log(error);
      throw new Error("Error creating order");
    }
  },
};
