"use client";
import React, { useEffect, useState } from "react";
import { useShopAddModal } from "@/hooks/shop/add.hook";
import Drawer from "@/components/ui/drawer";
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectLabel,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Button } from "@/components/ui/button";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { CreateShopSchema } from "@/lib/validation";
import { zodResolver } from "@hookform/resolvers/zod";
import { Input } from "@/components/ui/input";
import useFetch from "@/hooks/fetcher";
import { UserType } from "@/types/user.type";
import { formatPhoneNumber } from "@/lib/utils";
import { CrudShopService } from "@/services/shop/crud.service";
import { toast } from "react-toastify";
import { useRouter } from "next/navigation";

const AddShopDrawer = () => {
  const router = useRouter();
  const { setOpen, open } = useShopAddModal();
  const [managers, setManagers] = useState<UserType[]>([]);

  const { data: fetchManagers } = useFetch(`/user/sellers/`);

  useEffect(() => {
    if (fetchManagers) {
      setManagers(fetchManagers);
    }
  }, [fetchManagers]);

  const form = useForm<z.infer<typeof CreateShopSchema>>({
    resolver: zodResolver(CreateShopSchema),
    defaultValues: {
      name: "",
      logo: "",
      banner: "",
    },
  });

  async function onSubmit(values: z.infer<typeof CreateShopSchema>) {
    const data = {
      name: values.name,
      logo: values.logo,
      banner: values.banner,
      manager: Number(values.manager),
    };

    try {
      //@ts-ignore
      const status = await CrudShopService.createShop(data);

      if (status) {
        toast.success("Successfully created!");
        router.refresh();
        setOpen(open);
      }
    } catch (error: any) {
      toast.error("Failed to create shop");
    }
  }

  const { isSubmitting } = form.formState;
  const body = (
    <>
      <Form {...form}>
        <form
          className={`flex flex-col h-[90vh] px-3 justify-between`}
          onSubmit={form.handleSubmit(onSubmit)}
        >
          <div className={`mt-4 flex flex-col gap-y-5`}>
            <FormField
              control={form.control}
              name="logo"
              render={({ field }) => (
                <FormItem>
                  <FormLabel htmlFor={field.name}>Logo of Shop</FormLabel>
                  <FormControl>
                    {/*@ts-ignore*/}
                    <Input
                      // @ts-ignore
                      onChange={(e) => field.onChange(e.target.files?.[0])}
                      type={"file"}
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <FormField
              control={form.control}
              name="banner"
              render={({ field }) => (
                <FormItem>
                  <FormLabel htmlFor={field.name}>Banner of Shop</FormLabel>
                  <FormControl>
                    {/*@ts-ignore*/}
                    <Input
                      // @ts-ignore
                      onChange={(e) => field.onChange(e.target.files?.[0])}
                      type={"file"}
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <FormField
              control={form.control}
              name="name"
              render={({ field }) => (
                <FormItem>
                  <FormLabel htmlFor={field.name}>Name of Shop</FormLabel>
                  <FormControl>
                    <Input placeholder={`Type shop name`} {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <FormField
              control={form.control}
              name="manager"
              render={({ field }) => (
                <FormItem>
                  <FormLabel htmlFor={field.name}>Manager</FormLabel>
                  <FormControl>
                    <Select
                      name={field.name}
                      onValueChange={(e: string) => field.onChange(e)}
                    >
                      <SelectTrigger>
                        <SelectValue placeholder="Select a Sellers" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectGroup>
                          <SelectLabel>Sellers</SelectLabel>
                          {managers.map((i) => (
                            <SelectItem key={i.id} value={`${i.id}`}>
                              {formatPhoneNumber(i.phone_number)}
                            </SelectItem>
                          ))}
                        </SelectGroup>
                      </SelectContent>
                    </Select>
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
          </div>

          <Button disabled={isSubmitting} className={`w-full`}>
            Create
          </Button>
        </form>
      </Form>
    </>
  );

  return (
    <Drawer title={"Add Shop"} open={open} setOpen={setOpen} body={body} />
  );
};

export default AddShopDrawer;
