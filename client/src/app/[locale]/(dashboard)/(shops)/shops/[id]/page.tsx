"use client";
import React, { useEffect, useState } from "react";
import AnimatedValue from "@/components/ui/counter";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { formatPhoneNumber } from "@/lib/utils";
import { useParams, useRouter } from "next/navigation";
import useFetch from "@/hooks/fetcher";
import { ShopDetailType } from "@/types/shops.type";
import Img from "@/components/media/image";
import { ShopsAnalyticsType } from "@/types/analytics.type";
import { useEditShop } from "@/hooks/shop/edit.hook";
import { TbEdit } from "react-icons/tb";
import { FiMinusCircle } from "react-icons/fi";
import { useDeleteShop } from "@/hooks/shop/delete.hook";
import { Button } from "@/components/ui/button";
import { LuSettings2 } from "react-icons/lu";
import { IoIosAddCircleOutline } from "react-icons/io";

const Page = () => {
  const router = useRouter();
  const shopEdit = useEditShop();
  const shopDelete = useDeleteShop();

  const { id } = useParams<{ id: string }>();

  const [shop, setShop] = useState<ShopDetailType>();
  const [analytics, setAnalytics] = useState<ShopsAnalyticsType>();
  const [settings, setSettings] = useState<boolean>(false);

  const { data: fetchShop } = useFetch(`/shops/${id}`);
  const { data: fetchAnalytics } = useFetch(`/analytics/shops/${id}/`);

  useEffect(() => {
    if (fetchShop) {
      setShop(fetchShop);
    }
    if (fetchAnalytics) {
      setAnalytics(fetchAnalytics);
    }
  }, [fetchShop, fetchAnalytics]);

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
      <div className={`mb-28`}>
        {(shop?.banner || shop?.logo || shop) && (
          <div className={`w-full relative h-[300px] bg-accent`}>
            {shop?.banner && (
              <Img
                src={shop?.banner}
                className={`w-full h-[300px] object-cover`}
                alt={`banner`}
              />
            )}
            {shop?.logo ? (
              <Img
                className={`absolute bg-accent border border-accent-foreground left-24 z-10 -bottom-20 rounded-full object-cover p-3 shadow-md  w-40 h-40`}
                src={shop.logo}
                alt={`logo`}
              />
            ) : (
              <div
                className={`absolute bg-accent border border-accent-foreground left-24 z-10 -bottom-20 rounded-full object-cover p-3 shadow-md  w-40 h-40`}
              ></div>
            )}
            <div
              className={`absolute border border-accent-foreground flex flex-col items-start justify-between left-56 px-12 pl-12 bg-accent rounded-lg py-4 -bottom-14 h-28`}
            >
              <p className={`uppercase text-3xl font-semibold`}>{shop.name}</p>

              {shop.manager ? (
                <p className={`font-medium`}>
                  {formatPhoneNumber(shop.manager?.phone_number)}
                </p>
              ) : (
                <p className={`font-medium`}>
                  {formatPhoneNumber(shop.owner.phone_number)}
                </p>
              )}
            </div>

            <div
              className={`absolute -bottom-10 flex items-center gap-x-2 right-0`}
            >
              <button
                onClick={() => handlerEditOpen(Number(shop?.id))}
                className={`text-yellow-500 text-3xl duration-200 rounded hover:text-white hover:bg-yellow-500`}
              >
                <TbEdit />
              </button>
              <button
                onClick={() => handlerDeleteOpen(Number(shop?.id))}
                className={`text-red-500 text-3xl duration-200 rounded-full hover:text-white hover:bg-red-500`}
              >
                <FiMinusCircle />
              </button>
            </div>
          </div>
        )}
      </div>

      <div className={`w-full grid gap-x-2 grid-cols-4`}>
        {analytics && (
          <>
            <div
              className={`bg-background border flex flex-col justify-between p-4 rounded-lg h-[100px]`}
            >
              <p>Total Income:</p>
              <p
                className={`flex items-center text-3xl font-medium justify-center gap-x-2`}
              >
                UZS
                <AnimatedValue end={analytics.total_income} />
              </p>
            </div>
            <div
              className={`bg-background border flex flex-col justify-between p-4 rounded-lg h-[100px]`}
            >
              <p>Total Amount:</p>
              <p
                className={`flex items-center text-3xl font-medium justify-center gap-x-2`}
              >
                UZS
                <AnimatedValue end={analytics.total_amount} />
              </p>
            </div>
            <div
              className={`bg-background border flex flex-col justify-between p-4 rounded-lg h-[100px]`}
            >
              <p>Total Orders:</p>
              <p
                className={`flex items-center text-3xl font-medium justify-center gap-x-2`}
              >
                <AnimatedValue end={analytics.orders_count} />
              </p>
            </div>
            <div
              className={`bg-background border flex flex-col justify-between p-4 rounded-lg h-[100px]`}
            >
              <p>Total Products:</p>
              <p
                className={`flex items-center text-3xl font-medium justify-center gap-x-2`}
              >
                <AnimatedValue end={analytics.products_count} />
              </p>
            </div>
          </>
        )}
      </div>

      <Tabs defaultValue="orders" className="w-full mt-8">
        <TabsList>
          <TabsTrigger value="orders">Orders</TabsTrigger>
          <TabsTrigger value="products">Products</TabsTrigger>
        </TabsList>
        <TabsContent value="orders">
          <div className={`flex items-center my-5  justify-between`}>
            <p className={`text-2xl font-medium`}>
              Orders{" "}
              <span className={`align-super text-lg`}>
                ({shop?.orders.length})
              </span>
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
                onClick={() => router.push(`/shops/${id}/orders/create`)}
                size={"sm"}
              >
                <IoIosAddCircleOutline />
              </Button>
            </div>
          </div>

          <div className={`bg-background border rounded-lg`}>
            <Orders settings={settings} shop={shop} />
          </div>
        </TabsContent>
        <TabsContent value="products">
          <div className={`flex items-center my-5  justify-between`}>
            <p className={`text-2xl font-medium`}>
              Products{" "}
              <span className={`align-super text-lg`}>
                ({shop?.products.length})
              </span>
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
                onClick={() => router.push(`/shops/${id}/products/create`)}
                size={"sm"}
              >
                <IoIosAddCircleOutline />
              </Button>
            </div>
          </div>

          <div className={`bg-background border rounded-lg`}>
            <Products settings={settings} shop={shop} />
          </div>
        </TabsContent>
      </Tabs>
    </>
  );
};

export default Page;

const Products = ({
  settings,
  shop,
}: {
  settings: boolean;
  shop: ShopDetailType | undefined;
}) => {
  const router = useRouter();

  return (
    <>
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>ID</TableHead>
            <TableHead>Category</TableHead>
            <TableHead>Name</TableHead>
            <TableHead>Date</TableHead>
            <TableHead>Enter Price</TableHead>
            <TableHead>Out Price</TableHead>
            <TableHead>Count</TableHead>
            <TableHead className={`text-end`}>Expected income</TableHead>
            {settings && <TableHead className="text-right"></TableHead>}
          </TableRow>
        </TableHeader>
        <TableBody>
          {shop?.products.map((product, index) => (
            <TableRow className={`hover:bg-accent cursor-pointer`} key={index}>
              <TableCell
                onClick={() => router.push(`/products/${product.id}`)}
                className="font-medium"
              >
                ID-{product.id}
              </TableCell>
              <TableCell
                onClick={() => router.push(`/products/${product.id}`)}
                className={`uppercase`}
              >
                {product.category.name}
              </TableCell>
              <TableCell
                onClick={() => router.push(`/products/${product.id}`)}
                className={`uppercase`}
              >
                {product.name}
              </TableCell>
              <TableCell onClick={() => router.push(`/products/${product.id}`)}>
                {product.date_added}
              </TableCell>
              <TableCell onClick={() => router.push(`/products/${product.id}`)}>
                <p className="font-medium">
                  {Number(product.enter_price).toLocaleString("en-US", {
                    style: "currency",
                    currency: "uzs",
                  })}
                </p>
              </TableCell>
              <TableCell onClick={() => router.push(`/products/${product.id}`)}>
                <p className="font-medium">
                  {Number(product.out_price).toLocaleString("en-US", {
                    style: "currency",
                    currency: "uzs",
                  })}
                </p>
              </TableCell>
              <TableCell onClick={() => router.push(`/products/${product.id}`)}>
                <p className="font-medium">{product.count.toLocaleString()}</p>
              </TableCell>
              <TableCell className={`text-end`}>
                <p className="font-medium">
                  {(product.count * Number(product.enter_price)).toLocaleString(
                    "en-US",
                    {
                      style: "currency",
                      currency: "uzs",
                    },
                  )}
                </p>
              </TableCell>
              {settings && (
                <TableCell className="text-right w-fit flex items-center justify-end gap-x-2">
                  <button
                    // onClick={() => handlerEditOpen(shop.id)}
                    className={`text-yellow-500 text-xl duration-200 rounded hover:text-white hover:bg-yellow-500`}
                  >
                    <TbEdit />
                  </button>
                  <button
                    // onClick={() => handlerDeleteOpen(shop.id)}
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
    </>
  );
};

const Orders = ({
  settings,
  shop,
}: {
  settings: boolean;
  shop: ShopDetailType | undefined;
}) => {
  const router = useRouter();

  return (
    <>
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>ID</TableHead>
            <TableHead>Seller</TableHead>
            <TableHead>Products</TableHead>
            <TableHead>Date</TableHead>
            <TableHead>Amount</TableHead>
            <TableHead className="text-right">Income</TableHead>
            {settings && <TableHead className="w-[30px]"></TableHead>}
          </TableRow>
        </TableHeader>
        <TableBody>
          {shop?.orders
            .sort((a, b) => b.id - a.id)
            .map((order, index) => (
              <TableRow
                className={`hover:bg-accent cursor-pointer`}
                key={index}
              >
                <TableCell
                  onClick={() => router.push(`/orders/${order.id}`)}
                  className="font-medium"
                >
                  ID-{order.id}
                </TableCell>
                <TableCell
                  onClick={() => router.push(`/orders/${order.id}`)}
                  className={`uppercase`}
                >
                  {formatPhoneNumber(order.owner.phone_number)}
                </TableCell>
                <TableCell onClick={() => router.push(`/orders/${order.id}`)}>
                  {order.products.length}
                </TableCell>
                <TableCell onClick={() => router.push(`/orders/${order.id}`)}>
                  {order.date}
                </TableCell>
                <TableCell onClick={() => router.push(`/orders/${order.id}`)}>
                  <p className="font-medium">
                    {Number(order.total_price).toLocaleString("en-US", {
                      style: "currency",
                      currency: "uzs",
                    })}
                  </p>
                </TableCell>
                <TableCell
                  onClick={() => router.push(`/orders/${order.id}`)}
                  className="text-right"
                >
                  <p className="font-medium">
                    {Number(order.total_amount).toLocaleString("en-US", {
                      style: "currency",
                      currency: "uzs",
                    })}
                  </p>
                </TableCell>
                {settings && (
                  <TableCell className="text-right w-fit flex items-center justify-end gap-x-2">
                    <button
                      // onClick={() => handlerEditOpen(shop.id)}
                      className={`text-yellow-500 text-xl duration-200 rounded hover:text-white hover:bg-yellow-500`}
                    >
                      <TbEdit />
                    </button>
                  </TableCell>
                )}
              </TableRow>
            ))}
        </TableBody>
      </Table>
    </>
  );
};
