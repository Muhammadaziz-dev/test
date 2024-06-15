"use client";
import React from "react";
import { CrudShopService } from "@/services/shop/crud.service";
import { toast } from "react-toastify";
import { useDeleteShop } from "@/hooks/shop/delete.hook";
import AlertModel from "@/components/ui/alert-model";
import { useRouter } from "next/navigation";

const AlertDeleteShopModal = () => {
  const router = useRouter();
  const { open, setOpen, id } = useDeleteShop();

  const deleteShop = async () => {
    if (id) {
      try {
        const status = await CrudShopService.deleteShop(id);
        if (status) {
          toast.success("Successfully deleted!");
          router.refresh();
        }
      } catch (error: any) {}
    }
  };
  return (
    <>
      <AlertModel
        open={open}
        setOpen={setOpen}
        title={"Are you absolutely sure?\n"}
        message={
          "This action cannot be undone. This will permanently delete your account and remove your data from our servers."
        }
        continueClassName={`bg-red-500 hover:bg-red-600`}
        continueFunction={deleteShop}
      />
    </>
  );
};

export default AlertDeleteShopModal;
