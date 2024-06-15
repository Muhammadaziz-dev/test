import axios from "axios";
import { setCookie } from "@/lib/cookie";
import { PasswordResetSchema } from "@/lib/validation";

interface LoginData {
  phone_number?: string;
  password?: string;
}

interface LoginResponse {
  status: number;
  data: any;
}

export const AuthService = {
  async login(values: LoginData): Promise<LoginResponse> {
    try {
      const response = await axios.post(
        `${process.env.API}/user/login/`,
        values,
      );

      if (response.status === 200) {
        setCookie("token", response.data.token);
        localStorage.setItem("user", response.data.user);
      }

      return {
        status: response.status,
        data: response.data,
      };
    } catch (error: any) {
      throw new Error(`Error logging in: ${error.message}`);
    }
  },

  async resetPasswordRequest(phoneNumber: string) {
    try {
      const response = await axios.post(
        `${process.env.API}/user/reset/password/`,
        {
          phone_number: phoneNumber,
        },
      );

      return {
        status: response.status,
        data: response.data,
      };
    } catch (error: any) {
      throw new Error(`Error logging in: ${error.message}`);
    }
  },

  async passwordReset({
    newPassword,
    resetCode,
    phoneNumber,
  }: {
    newPassword: string;
    resetCode: string;
    phoneNumber: string;
  }) {
    try {
      const { data, status } = await axios.post(
        `${process.env.API}/user/reset/password/confirm/`,
        {
          phone_number: phoneNumber,
          reset_code: resetCode,
          new_password: newPassword,
        },
      );

      return {
        status: status,
        data: data,
      };
    } catch (error: any) {
      throw new Error(`Error logging in: ${error.message}`);
    }
  },
};
