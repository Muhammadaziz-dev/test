"use client";
import React, { useEffect, useState } from "react";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import PhoneInput from "react-phone-input-2";
import "react-phone-input-2/lib/style.css";
import { Button } from "@/components/ui/button";
import { IoIosAddCircleOutline } from "react-icons/io";
import { ProductType } from "@/types/product.type";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { TbEdit } from "react-icons/tb";
import { useParams } from "next/navigation";
import { OrderCrudService } from "@/services/order/crud.service";
import { toast } from "react-toastify";
import CreateOrderItemModal from "@/components/modals/order/create.modal";

const Page: React.FC = () => {
  const { id } = useParams<{ id: string }>();

  const [open, setOpen] = useState<boolean>(false);
  const [optionals, setOptionals] = useState<{
    phone_number: string;
    name: string;
  }>({
    phone_number: "",
    name: "",
  });
  const [settings, setSettings] = useState<boolean>(false);
  const [orderItems, setOrderItems] = useState<
    {
      product: string;
      quantity: string;
      price: number;
      productData: ProductType;
    }[]
  >([]);

  const data = {
    phone_number: optionals.phone_number,
    name: optionals.name,
    products: orderItems,
    shop: Number(id) as number,
  };

  const handleCreateOrder = async () => {
    try {
      const status = await OrderCrudService.create(data);

      if (status == 201) {
        toast.success("Order created successfully.");
        setOrderItems([]);
        setOptionals({
          phone_number: "",
          name: "",
        });
      }
    } catch (error: any) {
      console.log(error);
    }
  };

  return (
    <>
      <div className="container">
        <div className={`flex mb-5 items-center justify-between`}>
          <h2 className="mb-3 text-xl font-medium">Create new order</h2>
          <Button
            onClick={handleCreateOrder}
            disabled={!orderItems.length}
            size={"sm"}
          >
            Create Order
          </Button>
        </div>
        <div className="border bg-background w-full rounded-lg p-5">
          <OrderNameForm optionals={optionals} setOptionals={setOptionals} />
        </div>

        <div className="flex items-start my-4 justify-between">
          <h2 className="mb-3 text-xl font-medium">Order Products</h2>
          <Button
            onClick={() => setOpen(!open)}
            className="text-2xl w-8 h-8 p-0"
            size="sm"
          >
            <IoIosAddCircleOutline />
          </Button>
        </div>

        <div>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Product</TableHead>
                <TableHead>Enter Price</TableHead>
                <TableHead>Out Price</TableHead>
                <TableHead>Price</TableHead>
                <TableHead>Quantity</TableHead>
                <TableHead>Amount</TableHead>
                <TableHead className="text-right">Income</TableHead>
                {settings && <TableHead className="w-[30px]"></TableHead>}
              </TableRow>
            </TableHeader>
            <TableBody>
              {orderItems.map((order, index) => (
                <TableRow
                  className={`hover:bg-accent cursor-pointer`}
                  key={index}
                >
                  <TableCell className={`uppercase`}>
                    {order.productData.name}
                  </TableCell>
                  <TableCell>
                    {Number(order.productData.enter_price).toLocaleString(
                      "en-US",
                      {
                        style: "currency",
                        currency: "uzs",
                      },
                    )}
                  </TableCell>
                  <TableCell>
                    {Number(order.productData.out_price).toLocaleString(
                      "en-US",
                      {
                        style: "currency",
                        currency: "uzs",
                      },
                    )}
                  </TableCell>
                  <TableCell>
                    {Number(order.price).toLocaleString("en-US", {
                      style: "currency",
                      currency: "uzs",
                    })}
                  </TableCell>
                  <TableCell>
                    {Number(order.quantity).toLocaleString()}
                  </TableCell>
                  <TableCell>
                    {(
                      Number(order.quantity) * Number(order.price)
                    ).toLocaleString("en-US", {
                      style: "currency",
                      currency: "uzs",
                    })}
                  </TableCell>
                  <TableCell className={`text-right`}>
                    {(
                      Number(order.quantity) *
                      (Number(order.price) -
                        Number(order.productData.enter_price))
                    ).toLocaleString("en-US", {
                      style: "currency",
                      currency: "uzs",
                    })}
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
        </div>
      </div>
      <CreateOrderItemModal
        orderItems={orderItems}
        setOrderItems={setOrderItems}
        open={open}
        setOpen={setOpen}
      />
    </>
  );
};

export default Page;

const OrderNameForm = ({
  setOptionals,
  optionals,
}: {
  setOptionals: (e: any) => void;
  optionals: {
    phone_number: string;
    name: string;
  };
}) => {
  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { id, value } = e.target;
    setOptionals((prevState: any) => ({
      ...prevState,
      [id]: value,
    }));
  };

  const handlePhoneChange = (phone: string) => {
    setOptionals((prevState: any) => ({
      ...prevState,
      phone_number: phone,
    }));
  };

  return (
    <div className={`grid grid-cols-2 gap-x-3 items-center w-full`}>
      <div className="space-y-2">
        <Label htmlFor="name">Customer Name</Label>
        <Input
          id="name"
          value={optionals.name}
          onChange={handleInputChange}
          className="text-lg"
          placeholder="Type customer name"
        />
      </div>
      <div className="space-y-2 col-span-1">
        <Label htmlFor="CustomerPhoneNumber">Customer Phone Number</Label>
        <PhoneInput
          buttonClass="dark:bg-black hover:bg-black/70"
          inputClass="!w-full bg-white dark:bg-black rounded-lg py-5 text-lg font-normal"
          country={"uz"}
          onlyCountries={["uz"]}
          countryCodeEditable={false}
          masks={{ uz: "(..) ... - .. - .. " }}
          value={optionals.phone_number}
          onChange={handlePhoneChange}
        />
      </div>
    </div>
  );
};
