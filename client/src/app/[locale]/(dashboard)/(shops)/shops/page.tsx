"use client";
import React, { useEffect, useState } from "react";
import useFetch from "@/hooks/fetcher";
import { ShopsType } from "@/types/shops.type";
import { IoInformationOutline } from "react-icons/io5";
import { TbEdit } from "react-icons/tb";
import {
  Table,
  TableBody,
  TableCaption,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { formatPhoneNumber } from "@/lib/utils";
import AnimatedValue from "@/components/ui/counter";
import { ShopsAnalyticsType } from "@/types/analytics.type";
import { Button } from "@/components/ui/button";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { FiMinusCircle } from "react-icons/fi";
import { useShopAddModal } from "@/hooks/shop/add.hook";
import { IoIosAddCircleOutline } from "react-icons/io";
import { LuSettings2 } from "react-icons/lu";
import { useEditShop } from "@/hooks/shop/edit.hook";
import { useDeleteShop } from "@/hooks/shop/delete.hook";

const Page = () => {
  const router = useRouter();
  const shopAdd = useShopAddModal();
  const shopEdit = useEditShop();
  const shopDelete = useDeleteShop();
  const [shops, setShops] = useState<ShopsType[]>([]);
  const [analytics, setAnalytics] = useState<ShopsAnalyticsType>();
  const [settings, setSettings] = useState<boolean>(false);

  const { data: fetchShops } = useFetch(`/shops/`);
  const { data: fetchAnalytics } = useFetch(`/analytics/shops/`);

  useEffect(() => {
    if (fetchShops) {
      setShops(fetchShops);
    }

    if (fetchAnalytics) {
      setAnalytics(fetchAnalytics);
    }
  }, [fetchShops, fetchAnalytics]);

  function handlerEditOpen(id: number) {
    shopEdit.setOpen(shopEdit.open);
    shopEdit.setId(id);
  }

  function handlerDeleteOpen(id: number) {
    shopDelete.setOpen(shopDelete.open);
    shopDelete.setId(id);
  }

  return (
    <>
      <div className={`w-full grid gap-x-2 grid-cols-4`}>
        {analytics && (
          <>
            <div
              className={`border flex bg-background flex-col justify-between p-4 rounded-lg h-[100px]`}
            >
              <p>Total Amount:</p>
              <p
                className={`flex items-center text-3xl font-medium justify-center gap-x-2`}
              >
                UZS
                <AnimatedValue end={analytics.total_income} />
              </p>
            </div>
            <div
              className={`border flex bg-background flex-col justify-between p-4 rounded-lg h-[100px]`}
            >
              <p>Total Orders:</p>
              <p
                className={`flex items-center text-3xl font-medium justify-center gap-x-2`}
              >
                <AnimatedValue end={analytics.orders_count} />
              </p>
            </div>
            <div
              className={`border flex bg-background flex-col justify-between p-4 rounded-lg h-[100px]`}
            >
              <p>Total Products:</p>
              <p
                className={`flex items-center text-3xl font-medium justify-center gap-x-2`}
              >
                <AnimatedValue end={analytics.products_count} />
              </p>
            </div>
            <div
              className={`border flex bg-background flex-col justify-between p-4 rounded-lg h-[100px]`}
            >
              <p>Expected income:</p>
              <p
                className={`flex items-center text-3xl font-medium justify-center gap-x-2`}
              >
                UZS
                <AnimatedValue end={analytics.total_amount} />
              </p>
            </div>
          </>
        )}
      </div>

      <div className={`flex items-center my-5  justify-between`}>
        <p className={`text-2xl font-medium`}>
          Shops <span className={`align-super text-lg`}>({shops.length})</span>
        </p>
        <div>
          <Button
            variant={"ghost"}
            className={`text-2xl w-8 h-8 p-0`}
            onClick={() => setSettings(!settings)}
            size={"sm"}
          >
            <LuSettings2 />
          </Button>
          <Button
            className={`text-2xl w-8 h-8 p-0`}
            onClick={() => shopAdd.setOpen(shopAdd.open)}
            size={"sm"}
          >
            <IoIosAddCircleOutline />
          </Button>
        </div>
      </div>

      <div
        className={`border bg-background hover:shadow-md duration-200 rounded-lg mt-3`}
      >
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-[100px]">ID</TableHead>
              <TableHead>Name</TableHead>
              <TableHead>Products</TableHead>
              <TableHead>Orders</TableHead>
              <TableHead>Manager</TableHead>
              <TableHead className="text-right">Amount</TableHead>
              {settings && (
                <TableHead className="text-right w-[50px]"></TableHead>
              )}
            </TableRow>
          </TableHeader>
          <TableBody>
            {shops
              .sort((a, b) => a.id - b.id)
              .map((shop, index) => (
                <TableRow
                  className={`hover:bg-accent cursor-pointer`}
                  key={index}
                >
                  <TableCell
                    onClick={() => router.push(`/shops/${shop.id}`)}
                    className="font-medium"
                  >
                    ID-{shop.id}
                  </TableCell>
                  <TableCell
                    onClick={() => router.push(`/shops/${shop.id}`)}
                    className={`uppercase`}
                  >
                    {shop.name}
                  </TableCell>
                  <TableCell onClick={() => router.push(`/shops/${shop.id}`)}>
                    {shop.products_count}
                  </TableCell>
                  <TableCell onClick={() => router.push(`/shops/${shop.id}`)}>
                    {shop.orders_count}
                  </TableCell>
                  <TableCell onClick={() => router.push(`/shops/${shop.id}`)}>
                    {shop.manager_details
                      ? `${formatPhoneNumber(shop.manager_details?.phone_number)}`
                      : `${formatPhoneNumber(shop.owner.phone_number)}`}
                  </TableCell>
                  <TableCell
                    onClick={() => router.push(`/shops/${shop.id}`)}
                    className="text-right"
                  >
                    <p className="font-medium">
                      {shop.total_orders_value.toLocaleString("en-US", {
                        style: "currency",
                        currency: "uzs",
                      })}
                    </p>
                  </TableCell>
                  {settings && (
                    <TableCell className="text-right w-fit flex items-center justify-end gap-x-2">
                      <button
                        onClick={() => handlerEditOpen(shop.id)}
                        className={`text-yellow-500 text-xl duration-200 rounded hover:text-white hover:bg-yellow-500`}
                      >
                        <TbEdit />
                      </button>
                      <button
                        onClick={() => handlerDeleteOpen(shop.id)}
                        className={`text-red-500 text-xl duration-200 rounded-full hover:text-white hover:bg-red-500`}
                      >
                        <FiMinusCircle />
                      </button>
                    </TableCell>
                  )}
                </TableRow>
              ))}
          </TableBody>
        </Table>
      </div>
    </>
  );
};

export default Page;
