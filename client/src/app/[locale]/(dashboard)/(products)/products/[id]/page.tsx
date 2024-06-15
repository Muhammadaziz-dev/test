"use client";
import React, { useEffect, useState } from "react";
import { ProductType } from "@/types/product.type";
import useFetch from "@/hooks/fetcher";
import { useParams } from "next/navigation";
import Img from "@/components/media/image";

const Page = () => {
  const { id } = useParams<{ id: string }>();
  const [product, setProduct] = useState<ProductType>();

  const { data: fetchProduct } = useFetch(`/products/${id}`);

  useEffect(() => {
    if (fetchProduct) {
      setProduct(fetchProduct);
    }
  }, [fetchProduct]);

  return (
    <div className={`container`}>
      <h2 className={`mb-2 text-xl`}>Product</h2>
      <div
        className={`border mb-8 bg-background rounded-lg p-5 flex flex-col gap-y-3`}
      >
        <div
          className={`border-b border-dashed pb-2 flex justify-between items-center`}
        >
          <p className={`text-muted-foreground`}>ID</p>
          <h2 className={`text font-medium uppercase`}>ID-{product?.id}</h2>
        </div>
        <div
          className={`border-b border-dashed pb-2 flex justify-between items-center`}
        >
          <p className={`text-muted-foreground`}>Product Name</p>
          <h2 className={`text font-medium uppercase`}>{product?.name}</h2>
        </div>
        <div
          className={`border-b border-dashed pb-2 flex justify-between items-center`}
        >
          <p className={`text-muted-foreground`}>Category Name</p>
          <h2 className={`text font-medium uppercase`}>
            {product?.category.name}
          </h2>
        </div>
        <div
          className={`border-b border-dashed pb-2 flex justify-between items-center`}
        >
          <p className={`text-muted-foreground`}>Date</p>
          <h2 className={`text font-medium uppercase`}>
            {product?.date_added}
          </h2>
        </div>
        <div
          className={`border-b border-dashed pb-2 flex justify-between items-center`}
        >
          <p className={`text-muted-foreground`}>Count</p>
          <h2 className={`text font-medium uppercase`}>
            {Number(product?.count).toLocaleString()}
          </h2>
        </div>
        <div
          className={`border-b border-dashed pb-2 flex justify-between items-center`}
        >
          <p className={`text-muted-foreground`}>Enter Price</p>
          <h2 className={`text font-medium uppercase`}>
            {Number(product?.enter_price).toLocaleString("en-US", {
              style: "currency",
              currency: "uzs",
            })}
          </h2>
        </div>
        <div
          className={`border-b border-dashed pb-2 flex justify-between items-center`}
        >
          <p className={`text-muted-foreground`}>Out Price</p>
          <h2 className={`text font-medium uppercase`}>
            {Number(product?.out_price).toLocaleString("en-US", {
              style: "currency",
              currency: "uzs",
            })}
          </h2>
        </div>
      </div>

      {product?.properties && (
        <>
          <h2 className={`mb-2 text-xl`}>Properties</h2>
          <div
            className={`border mb-8 bg-background rounded-lg p-5 flex flex-col gap-y-3`}
          >
            {product.properties.map((prop) => (
              <div
                key={prop.id}
                className={`border-b border-dashed pb-2 flex justify-between items-center`}
              >
                <p className={`text-muted-foreground capitalize`}>
                  {prop.feature}
                </p>
                <h2 className={`text font-medium uppercase`}>{prop.value}</h2>
              </div>
            ))}
          </div>
        </>
      )}

      {product?.images && (
        <>
          <h2 className={`mb-2 text-xl`}>Images</h2>
          <div
            className={`border mb-8 bg-background rounded-lg p-5 grid grid-cols-5 gap-3`}
          >
            {product.images.map((image) => (
              <Img
                key={image.id}
                src={`http://127.0.0.1:8000${image.image}`}
                alt={`${image.id}-${product.id}`}
              />
            ))}
          </div>
        </>
      )}
    </div>
  );
};

export default Page;
