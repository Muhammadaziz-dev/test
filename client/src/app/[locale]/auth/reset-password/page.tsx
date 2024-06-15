"use client";
import React from "react";
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import PhoneInput from "react-phone-input-2";
import { Button } from "@/components/ui/button";
import { FaArrowRight } from "react-icons/fa";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import { AuthService } from "@/services/auth/login.service";
import { toast } from "react-toastify";
import { PasswordResetRequestSchema } from "@/lib/validation";
import { useRouter } from "next/navigation";
import { useReset } from "@/hooks/auth/reset.db";

const Page = () => {
  const router = useRouter();
  const { setPhone_number } = useReset();
  const form = useForm<z.infer<typeof PasswordResetRequestSchema>>({
    resolver: zodResolver(PasswordResetRequestSchema),
    defaultValues: {
      phone_number: "",
    },
  });

  async function onSubmit(values: z.infer<typeof PasswordResetRequestSchema>) {
    try {
      const { status, data } = await AuthService.resetPasswordRequest(
        values.phone_number,
      );

      if (status === 200) {
        toast.success(`${data.message}`);
        setPhone_number(values.phone_number);
        router.push("/auth/reset-password/confirm");
      }
    } catch (error: any) {
      toast.error(`${error}`);
    }
  }

  const { isSubmitting } = form.formState;

  return (
    <>
      <Form {...form}>
        <form
          onSubmit={form.handleSubmit(onSubmit)}
          className="space-y-5 w-8/12 mx-auto"
        >
          <div className={`relative`}>
            <FormField
              control={form.control}
              name="phone_number"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Phone Number</FormLabel>
                  <FormControl>
                    <PhoneInput
                      buttonClass={"dark:!bg-black !hover:bg-black/70"}
                      inputClass={`!w-full bg-white dark:!bg-black !rounded-lg !py-5 !text-xl !font-normal`}
                      country={"uz"}
                      onlyCountries={["uz"]}
                      countryCodeEditable={false}
                      masks={{ uz: "(..) ... - .. - .. " }}
                      value={field.value}
                      onChange={(phone) => field.onChange(phone)}
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
