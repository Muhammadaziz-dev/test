import axios from "axios";
import { getCookie } from "@/lib/cookie";

const token = getCookie("token");

const fetcher = async (url: string) => {
  try {
    const response = await axios.get(`${process.env.API + url}`, {
      headers: {
        "Content-Type": "application/json",
        Authorization: token ? `Token ${token}` : "",
      },
    });
    return response.data;
  } catch (error) {
    throw error;
  }
};

export default fetcher;
