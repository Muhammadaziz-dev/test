"use client";
import React from "react";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import { AuthService } from "@/services/auth/login.service";
import { toast } from "react-toastify";
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { Button } from "@/components/ui/button";
import { FaArrowRight } from "react-icons/fa";
import { PasswordResetSchema } from "@/lib/validation";
import { useReset } from "@/hooks/auth/reset.db";
import { Input } from "@/components/ui/input";
import VerificationInput from "react-verification-input";
import ResetPage from "@/app/[locale]/auth/reset-password/page";

const Page = () => {
  const { phone_number } = useReset();
  const router = useRouter();
  const form = useForm<z.infer<typeof PasswordResetSchema>>({
    resolver: zodResolver(PasswordResetSchema),
    defaultValues: {
      new_password: "",
      reset_code: "",
    },
  });

  async function onSubmit(values: z.infer<typeof PasswordResetSchema>) {
    try {
      const validData = {
        newPassword: values.new_password,
        resetCode: values.reset_code,
        phoneNumber: phone_number,
      };

      const { status, data } = await AuthService.passwordReset(validData);

      if (status === 200) {
        toast.success(`${data.message}`);
        router.push("/auth/login");
      }
    } catch (error: any) {
      toast.error(`${error}`);
    }
  }

  const { isSubmitting } = form.formState;

  if (!phone_number) {
    return <ResetPage />;
  }

  return (
    <>
      <Form {...form}>
        <form
          onSubmit={form.handleSubmit(onSubmit)}
          className="space-y-5 w-8/12 mx-auto"
        >
          <FormField
            control={form.control}
            name="reset_code"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Code</FormLabel>
                <FormControl>
                  <div className={`flex items-center justify-center`}>
                    <VerificationInput
                      validChars="0-9"
                      inputProps={{ inputMode: "numeric" }}
                      autoFocus={true}
                      placeholder="X"
                      classNames={{ character: "rounded-lg" }}
                      {...field}
                    />
                  </div>
                </FormControl>

                <FormMessage />
              </FormItem>
            )}
          />
          <div className={`relative`}>
            <FormField
              control={form.control}
              name="new_password"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>New Password</FormLabel>
                  <FormControl>
                    <Input
                      autoComplete={field.value.toString()}
                      type={"password"}
                      placeholder={`Type new password`}
                      {...field}
                    />
                  </FormControl>

                  <FormMessage />
                </FormItem>
              )}
            />
            <Button
              disabled={isSubmitting}
              size="sm"
              className={`absolute right-1 text-xl w-9 h-9 !p-0 top-9 rounded-full`}
            >
              <FaArrowRight />
            </Button>
          </div>
        </form>
      </Form>
    </>
  );
};

export default Page;
