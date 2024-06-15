"use client";
import React from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { LoginSchema } from "@/lib/validation";
import { zodResolver } from "@hookform/resolvers/zod";
import { toast } from "react-toastify";
import { AuthService } from "@/services/auth/login.service";
import PhoneInput from "react-phone-input-2";
import { FaArrowRight } from "react-icons/fa";
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useRouter } from "next/navigation";
import { useUser } from "@/hooks/user/user.db";
import { UserType } from "@/types/user.type";
import { IoFingerPrint } from "react-icons/io5";
import Link from "next/link";
import { GoArrowUpRight } from "react-icons/go";

const Page = () => {
  const router = useRouter();
  const { setUser } = useUser();

  const form = useForm<z.infer<typeof LoginSchema>>({
    resolver: zodResolver(LoginSchema),
    defaultValues: {
      phone_number: "",
      password: "",
    },
  });

  async function onSubmit(values: z.infer<typeof LoginSchema>) {
    try {
      const { status, data } = await AuthService.login(values);

      if (status === 200) {
        setUser(data as UserType);
        toast.success(`${data.message}`);
        router.push("/");
        router.refresh();
      }
    } catch (error: any) {
      toast.error(`${error}`);
    }
  }

  const { isSubmitting } = form.formState;

  return (
    <div className={`relative `}>
      <p
        className={`absolute text-xl uppercase font-semibold top-2 left-2 cursor-pointer`}
      >
        MF Platform
      </p>
      <div
        className={`h-screen bg-accent dark:bg-gray-950 w-full flex items-center justify-center`}
      >
        <div
          className={`w-5/12 bg-background h-[500px] px-5 flex flex-col justify-evenly items-center border shadow-lg rounded-3xl`}
        >
          <div className={`space-y-3`}>
            <span className={`flex items-center justify-center`}>
              <IoFingerPrint
                className={`text-[80px] shadow text-white bg-gradient-to-r from-cyan-500 to-blue-500 border rounded-full p-2`}
              />
            </span>
            <h1 className={`text-center select-none text-2xl font-medium`}>
              Sign in MF Platform
            </h1>
          </div>
          <Form {...form}>
            <form
              onSubmit={form.handleSubmit(onSubmit)}
              className="space-y-5 w-8/12 mx-auto"
            >
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
                        value={field.value} // Pass field value to PhoneInput
                        onChange={(phone) => field.onChange(phone)} // Update field value on change
                      />
                    </FormControl>

                    <FormMessage />
                  </FormItem>
                )}
              />
              <div className={`relative`}>
                <FormField
                  control={form.control}
                  name="password"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Password</FormLabel>
                      <FormControl>
                        <Input
                          autoComplete={field.value.toString()}
                          type={"password"}
                          {...field}
                          placeholder={`Type your Password`}
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
          <div className={`flex flex-col items-center justify-between gap-y-2`}>
            <Link
              target={"_blank"}
              className={`text-blue-500 flex items-end font-light hover:underline underline-offset-2`}
              href={`/auth/reset-password`}
            >
              Forgot password? <GoArrowUpRight />
            </Link>
            <Link
              className={`text-blue-500 flex items-end font-light hover:underline underline-offset-2`}
              href={`/contact/case/`}
            >
              Apply for account creation
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Page;
