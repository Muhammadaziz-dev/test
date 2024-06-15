import { z } from "zod";

export const LoginSchema = z.object({
  phone_number: z.string().min(12).max(12),
  password: z.string().min(4),
});

export const PasswordResetRequestSchema = z.object({
  phone_number: z.string().min(12).max(12),
});

export const PasswordResetSchema = z.object({
  new_password: z.string().min(4),
  reset_code: z.string().min(6).max(6),
});

export const CreateShopSchema = z.object({
  name: z.string().min(2),
  manager: z.string().optional(),
  logo: z.unknown().optional(),
  banner: z.unknown().optional(),
});

export const UpdateShopSchema = z.object({
  name: z.string().optional(),
  manager: z.string().optional(),
  logo: z.unknown().optional(),
  banner: z.unknown().optional(),
});

export const CreateOrderSchema = z.object({
  name: z.string().optional(),
  phone_number: z.string().min(12).max(12).optional(),
});
