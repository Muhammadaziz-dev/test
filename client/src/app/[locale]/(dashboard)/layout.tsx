"use client";
import React, { useEffect, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import Sidebar from "@/components/sidebar";
import Toolbar from "@/components/tool-bar";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { getCookie, removeCookie } from "@/lib/cookie";
import AlertDeleteShopModal from "@/components/alert-model/shop/alert";
import AddShopDrawer from "@/components/drawers/shop/add.drawer";
import EditShopDrawer from "@/components/drawers/shop/edit.drawer";

const links = [
  {
    label: "Dashboard",
    path: "/",
  },
  {
    label: "Shops",
    path: "/shops",
  },
  {
    label: "Sellers",
    path: "/sellers",
  },
  {
    label: "Loans",
    path: "/loans",
  },
  {
    label: "Products",
    path: "/products",
  },
];

const Layout = ({ children }: { children: React.ReactNode }) => {
  const location = usePathname();
  const router = useRouter();

  const [time, setTime] = useState(
    typeof window !== "undefined" ? new Date() : null,
  );
  const [show, setShow] = useState(false);

  useEffect(() => {
    if (typeof window !== "undefined") {
      const intervalID = setInterval(() => {
        setTime(new Date());
      }, 1000);

      return () => clearInterval(intervalID);
    }
  }, []);

  const formatTime = (time: Date) => {
    return time.toLocaleTimeString([], {
      hour: "2-digit",
      minute: "2-digit",
      hour12: false,
    });
  };

  function logout() {
    removeCookie("token");
    localStorage.removeItem("user");
    router.push("/auth/login");
  }

  useEffect(() => {
    setShow(true);
  }, []);

  const [isTokenChecked, setIsTokenChecked] = useState(false);

  useEffect(() => {
    const token = getCookie("token");

    if (!token) {
      router.push("/auth/login");
    } else {
      setIsTokenChecked(true);
    }
  }, [router]);

  if (!isTokenChecked) {
    return null;
  }

  return (
    <>
      <Sidebar links={links} />
      <Toolbar />
      <main className={`min-h-screen mr-[5%] ml-[20%]`}>
        <header
          className={`border-b bg-background/80 backdrop-blur-md z-50 sticky top-0 py-2`}
        >
          <div
            className={`container grid grid-cols-3 items-center justify-between`}
          >
            <h1 className={`text-xl font-medium uppercase`}>
              {links.filter((i) => i.path === location).map((i) => i.label)}
            </h1>
            <div className="text-center py-0.5 hover:bg-secondary px-2 duration-200 cursor-pointer rounded-lg">
              <p className="text-3xl">{show && time && formatTime(time)}</p>
            </div>
            <div className={`flex items-center justify-end gap-x-4`}>
              <DropdownMenu>
                <DropdownMenuTrigger
                  className={`bg-secondary select-none rounded-lg py-2 px-4`}
                >
                  Humoyunbek
                </DropdownMenuTrigger>
                <DropdownMenuContent>
                  <DropdownMenuLabel>My Account</DropdownMenuLabel>
                  <DropdownMenuSeparator />
                  <DropdownMenuItem>Profile</DropdownMenuItem>
                  <DropdownMenuItem>Billing</DropdownMenuItem>
                  <DropdownMenuItem>Team</DropdownMenuItem>
                  <DropdownMenuItem
                    onClick={logout}
                    className={`bg-red-500 font-medium hover:!bg-red-600`}
                  >
                    Logout
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            </div>
          </div>
        </header>
        <div className={`px-2 dark:bg-gray-950 py-4`}>{children}</div>
      </main>

      <AlertDeleteShopModal />
      <AddShopDrawer />
      <EditShopDrawer />
    </>
  );
};

export default Layout;
