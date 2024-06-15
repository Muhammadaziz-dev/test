import axios from "axios";
import { getCookie } from "@/lib/cookie";

const token = getCookie("token");

export const CrudShopService = {
  async createShop(values: ShopType): Promise<number> {
    const formData = new FormData();
    formData.append("name", values.name);
    if (values.logo && values.logo !== "") {
      formData.append("logo", values.logo);
    }
    if (values.banner && values.banner !== "") {
      formData.append("banner", values.banner);
    }
    if (values.manager && !isNaN(values.manager)) {
      formData.append("manager", values.manager.toString());
    }

    try {
      const { status } = await axios.post(
        `${process.env.API}/shops/create/`,
        formData,
        {
          headers: {
            "Content-Type": "multipart/form-data",
            Authorization: `Token ${token}`,
          },
        },
      );
      return status;
    } catch (error: any) {
      console.log(error);
      throw new Error(`Error: ${error.message}`);
    }
  },

  async updateShop(values: ShopType, id: number): Promise<number> {
    const formData = new FormData();
    formData.append("name", values.name);
    if (values.logo && values.logo !== "") {
      formData.append("logo", values.logo);
    }
    if (values.banner && values.banner !== "") {
      formData.append("banner", values.banner);
    }
    if (values.manager && !isNaN(values.manager)) {
      formData.append("manager", values.manager.toString());
    }

    try {
      const { status } = await axios.patch(
        `${process.env.API}/shops/${id}/update/`,
        formData,
        {
          headers: {
            "Content-Type": "multipart/form-data",
            Authorization: `Token ${token}`,
          },
        },
      );
      return status;
    } catch (error: any) {
      console.log(error);
      throw new Error(`Error: ${error.message}`);
    }
  },

  async deleteShop(id: number): Promise<number> {
    try {
      const { status } = await axios.delete(
        `${process.env.API}/shops/${id}/delete/`,
        {
          headers: {
            "Content-Type": "application/json",
            Authorization: `Token ${token}`,
          },
        },
      );
      return status;
    } catch (error: any) {
      console.log(error);
      throw new Error(`Error: ${error.message}`);
    }
  },
};

interface ShopType {
  name: string;
  logo?: File | string;
  banner?: File | string;
  manager?: number;
}
