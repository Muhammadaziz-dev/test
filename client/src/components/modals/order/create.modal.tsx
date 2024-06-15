import React, { useEffect, useState } from "react";
import { ProductType } from "@/types/product.type";
import useFetch from "@/hooks/fetcher";
import axios from "axios";
import { Label } from "@/components/ui/label";
import Combobox from "@/components/ui/combobox";
import { Input } from "@/components/ui/input";
import CurrencyInput from "react-currency-input-field";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Button } from "@/components/ui/button";
import Modal from "@/components/ui/modal";

interface OrderItemType {
  product: string;
  quantity: string;
  price: number;
  productData: ProductType;
}

interface Props {
  open: boolean;
  setOpen: (open: boolean) => void;
  setOrderItems: (orderItems: OrderItemType[]) => void;
  orderItems: OrderItemType[];
}

interface OrderItemState {
  product: string;
  quantity: string;
  price: number;
}

const CreateOrderItemModal: React.FC<Props> = ({
  open,
  setOpen,
  orderItems,
  setOrderItems,
}) => {
  const [products, setProducts] = useState<ProductType[]>([]);
  const { data: fetchProducts } = useFetch("/products/");
  const [currency, setCurrency] = useState<string>("usd");
  const [exchangeRate, setExchangeRate] = useState<number>(1);
  const [orderItem, setOrderItem] = useState<OrderItemState>({
    product: "",
    quantity: "",
    price: 0,
  });

  useEffect(() => {
    if (fetchProducts) setProducts(fetchProducts);
  }, [fetchProducts]);

  useEffect(() => {
    const fetchCurrency = async () => {
      try {
        const res = await axios.get(
          `https://api.exchangerate-api.com/v4/latest/USD`,
        );
        setExchangeRate(res.data.rates.UZS);
      } catch (error) {
        console.log(error);
      }
    };

    if (currency === "uzs") {
      fetchCurrency();
    } else {
      setExchangeRate(1);
    }
  }, [currency]);

  const formatCurrency = (value: number, currency: string) => {
    return Number(value).toLocaleString("en-US", {
      style: "currency",
      currency: currency,
    });
  };

  const options = products.map((product) => ({
    value: product.id,
    label: `${product.name} - ${formatCurrency(
      Number(product.enter_price),
      product.currency,
    )} - ${formatCurrency(Number(product.out_price), product.currency)} (${
      product.count
    })`,
  }));

  const handleOrderItemChange = (value: string) => {
    const selectedProduct = products.find(
      (product) => product.id === Number(value),
    );
    if (selectedProduct) {
      setOrderItem({
        product: value,
        quantity: "1",
        price: Number(selectedProduct.out_price),
      });
    }
  };

  const addOrderItem = () => ({
    product: orderItem.product,
    quantity: orderItem.quantity,
    price: orderItem.price,
    productData: products.find(
      (product) => product.id === Number(orderItem.product),
    )!,
  });

  const handlePushItem = () => {
    setOrderItems([...orderItems, addOrderItem()]);
    resetOrderItem();
    setOpen(false);
  };

  const handlePushItemAndOtherAdd = () => {
    setOrderItems([...orderItems, addOrderItem()]);
    resetOrderItem();
  };

  const resetOrderItem = () => {
    setOrderItem({ product: "", quantity: "", price: 0 });
  };

  const selectedProduct = products.find(
    (product) => product.id === Number(orderItem.product),
  );

  const body = (
    <div className="mt-4 container space-y-4">
      <div className="space-y-2">
        <Label htmlFor="products">Product</Label>
        <Combobox
          id="products"
          value={orderItem.product}
          onChange={handleOrderItemChange}
          placeholder="Select Product"
          options={options}
        />
      </div>
      <div className="mt-4">
        <Label htmlFor="quantity">Quantity</Label>
        {selectedProduct &&
          Number(orderItem.quantity) >= selectedProduct.count && (
            <div className="text-red-500 text-sm">
              The quantity exceeds available stock!
            </div>
          )}
        <Input
          id="quantity"
          value={orderItem.quantity}
          onChange={(e) =>
            setOrderItem({ ...orderItem, quantity: e.target.value })
          }
          type="number"
          min="1"
          className="mt-2"
        />
      </div>
      <div className="mt-4 grid gap-x-3 grid-cols-2 items-center justify-between">
        <div>
          <Label htmlFor="currency">Currency</Label>
          <Select
            defaultValue={currency}
            onValueChange={setCurrency}
            name="currency"
          >
            <SelectTrigger>
              <SelectValue placeholder="currency" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="usd">Dollar</SelectItem>
              <SelectItem value="uzs">{`So'm`}</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <div className="flex flex-col gap-y-2">
          <Label htmlFor="price">Price</Label>
          {selectedProduct &&
            Number(orderItem.price) <= Number(selectedProduct.enter_price) && (
              <div className="text-red-500 text-sm">
                You are selling at entry price
              </div>
            )}
          <CurrencyInput
            id="price"
            name="price"
            className="border uppercase px-2 focus:ring-0 focus:border focus:outline-primary py-1.5 rounded"
            prefix={`${currency.toUpperCase()} `}
            decimalScale={2}
            value={
              currency === "uzs"
                ? orderItem.price * exchangeRate
                : orderItem.price
            }
            decimalsLimit={3}
            decimalSeparator=","
            groupSeparator="."
            onValueChange={(value: any, name: any, values: any) =>
              setOrderItem({ ...orderItem, price: values.float / exchangeRate })
            }
            step={1}
          />
        </div>
      </div>
      {selectedProduct && (
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Product</TableHead>
              <TableHead>Quantity</TableHead>
              <TableHead>Amount</TableHead>
              <TableHead className="text-right">Income</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            <TableRow>
              <TableCell>{selectedProduct.name}</TableCell>
              <TableCell>{`${formatCurrency(
                orderItem.price,
                currency,
              )} x ${orderItem.quantity}`}</TableCell>
              <TableCell>
                {formatCurrency(
                  Number(orderItem.quantity) * orderItem.price,
                  currency,
                )}
              </TableCell>
              <TableCell className="text-right">
                {formatCurrency(
                  Number(orderItem.quantity) *
                    (orderItem.price - Number(selectedProduct.enter_price)),
                  currency,
                )}
              </TableCell>
            </TableRow>
          </TableBody>
        </Table>
      )}
      <div className="grid grid-cols-3 items-center gap-x-2">
        <Button
          onClick={handlePushItem}
          disabled={
            selectedProduct &&
            Number(orderItem.quantity) > Number(selectedProduct.count)
          }
          size="sm"
          variant="outline"
          className="w-full"
        >
          Add To Order
        </Button>
        <Button
          onClick={handlePushItemAndOtherAdd}
          size="sm"
          disabled={
            selectedProduct &&
            Number(orderItem.quantity) > Number(selectedProduct.count)
          }
          className="w-full col-span-2"
        >
          Add To Order and Another
        </Button>
      </div>
    </div>
  );

  return (
    <Modal
      className="min-w-[60%] w-fit max-w-[90%] min-h-[60%] max-h-[90%]"
      title="Add Order Item"
      open={open}
      setOpen={setOpen}
      body={body}
    />
  );
};

export default CreateOrderItemModal;
