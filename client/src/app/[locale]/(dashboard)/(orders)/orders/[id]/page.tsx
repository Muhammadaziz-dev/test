"use client";
import React, { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import useFetch from "@/hooks/fetcher";
import { OrderType } from "@/types/order.type";
import { formatPhoneNumber } from "@/lib/utils";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

const Page = () => {
  const { id } = useParams<{ id: string }>();
  const [order, setOrder] = useState<OrderType>();
  const router = useRouter();

  const { data: fetchOrder } = useFetch(`/orders/${id}/`);

  useEffect(() => {
    if (fetchOrder) {
      setOrder(fetchOrder);
    }
  }, [fetchOrder]);

  return (
    <div>
      <div className={`container`}>
        <div
          className={`w-full bg-background border flex flex-col gap-y-4 rounded-lg p-5 mb-6`}
        >
          <div
            className={`flex border-b-2 pb-2 border-dotted items-center justify-between`}
          >
            <p className={`text-muted-foreground`}>ID:</p>
            <p className={`font-medium`}>{order?.id}</p>
          </div>
          <div
            className={`flex border-b-2 pb-2 border-dotted items-center justify-between`}
          >
            <p className={`text-muted-foreground`}>Seller:</p>
            <p className={`font-medium`}>
              {formatPhoneNumber(String(order?.owner.phone_number))}
            </p>
          </div>
          <div
            className={`flex border-b-2 pb-2 border-dotted items-center justify-between`}
          >
            <p className={`text-muted-foreground`}>Date:</p>
            <p className={`font-medium`}>{order?.date}</p>
          </div>
          <div
            className={`flex border-b-2 pb-2 border-dotted items-center justify-between`}
          >
            <p className={`text-muted-foreground`}>Products:</p>
            <p className={`font-medium`}>{order?.products.length}</p>
          </div>
          <div
            className={`flex border-b-2 pb-2 border-dotted items-center justify-between`}
          >
            <p className={`text-muted-foreground`}>Total Amount:</p>
            <p className={`font-medium`}>
              {Number(order?.total_price).toLocaleString("en-US", {
                style: "currency",
                currency: "uzs",
              })}
            </p>
          </div>
          <div
            className={`flex border-b-2 pb-2 border-dotted items-center justify-between`}
          >
            <p className={`text-muted-foreground`}>Total Income:</p>
            <p className={`font-medium`}>
              {Number(order?.total_amount).toLocaleString("en-US", {
                style: "currency",
                currency: "uzs",
              })}
            </p>
          </div>
        </div>
        <div className={`border bg-background p-3 rounded-lg`}>
          <Table>
            <TableHeader>
              <TableRow className={`text-start`}>
                <TableHead className={`w-[30px]`}>ID</TableHead>
                <TableHead>Name</TableHead>
                <TableHead>Enter Price</TableHead>
                <TableHead>Quantity</TableHead>
                <TableHead>Price</TableHead>
                <TableHead>Amount</TableHead>
                <TableHead className={`text-end`}>Income</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {order?.products.map((product, index) => (
                <TableRow
                  onClick={() =>
                    router.push(`/products/${product.product_data.id}`)
                  }
                  className={`hover:bg-accent text-start cursor-pointer`}
                  key={index}
                >
                  <TableCell className="font-medium">
                    {product.product_data.id}
                  </TableCell>
                  <TableCell className={`uppercase`}>
                    {product.product_data.name}
                  </TableCell>
                  <TableCell>
                    <p className="font-medium">
                      {Number(product.product_data.enter_price).toLocaleString(
                        "en-US",
                        {
                          style: "currency",
                          currency: "uzs",
                        },
                      )}
                    </p>
                  </TableCell>
                  <TableCell>
                    <p className="font-medium">{product.quantity}</p>
                  </TableCell>
                  <TableCell>
                    <p className="font-medium">
                      {Number(product.price).toLocaleString("en-US", {
                        style: "currency",
                        currency: "uzs",
                      })}
                    </p>
                  </TableCell>
                  <TableCell>
                    <p className="font-medium">
                      {(
                        Number(product.price) * product.quantity
                      ).toLocaleString("en-US", {
                        style: "currency",
                        currency: "uzs",
                      })}
                    </p>
                  </TableCell>
                  <TableCell className={`text-end`}>
                    <p className="font-medium">
                      {(
                        Number(product.price) * product.quantity -
                        Number(product.product_data.enter_price) *
                          product.quantity
                      ).toLocaleString("en-US", {
                        style: "currency",
                        currency: "uzs",
                      })}
                    </p>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      </div>
    </div>
  );
};

export default Page;
