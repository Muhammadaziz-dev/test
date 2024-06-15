"use client";
import React, { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { UserType } from "@/types/user.type";
import useFetch from "@/hooks/fetcher";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { UpdateShopSchema } from "@/lib/validation";
import { zodResolver } from "@hookform/resolvers/zod";
import { CrudShopService } from "@/services/shop/crud.service";
import { toast } from "react-toastify";
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectLabel,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { formatPhoneNumber } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import Drawer from "@/components/ui/drawer";
import { useEditShop } from "@/hooks/shop/edit.hook";
import { ShopDetailType } from "@/types/shops.type";

const EditShopDrawer = () => {
  const router = useRouter();
  const { setOpen, open, id } = useEditShop();

  const [shop, setShop] = useState<ShopDetailType>();
  const [managers, setManagers] = useState<UserType[]>([]);

  const { data: fetchShop } = useFetch(id ? `/shops/${id}/` : "/shops/");
  const { data: fetchManagers } = useFetch(`/user/sellers/`);

  useEffect(() => {
    if (fetchShop) {
      setShop(fetchShop);
    }

    if (fetchManagers) {
      setManagers(fetchManagers);
    }
  }, [fetchManagers, fetchShop]);

  const form = useForm<z.infer<typeof UpdateShopSchema>>({
    resolver: zodResolver(UpdateShopSchema),
    defaultValues: {
      name: shop?.name,
      logo: shop?.logo,
      banner: shop?.banner,
      manager: `${shop?.manager?.id}`,
    },
  });

  async function onSubmit(values: z.infer<typeof UpdateShopSchema>) {
    const data = {
      name: values.name as string,
      logo: values.logo as File,
      banner: values.banner as File,
      manager: Number(values.manager),
    };

    try {
      const status = await CrudShopService.updateShop(data, Number(id));

      if (status) {
        toast.success("Successfully created!");
        router.refresh();
        setOpen(open);
      }
    } catch (error: any) {
      toast.error(error);
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
                    <Input
                      defaultValue={shop?.name as string}
                      placeholder={`Type shop name`}
                      {...field}
                    />
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
                      defaultValue={`${shop?.manager?.id}`}
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
    <Drawer title={"Edit Shop"} open={open} setOpen={setOpen} body={body} />
  );
};

export default EditShopDrawer;
