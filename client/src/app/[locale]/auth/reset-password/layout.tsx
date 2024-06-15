import React from "react";
import { IoFingerPrint } from "react-icons/io5";
import Link from "next/link";
import { GoArrowUpRight } from "react-icons/go";

const Layout = ({ children }: { children: React.ReactNode }) => {
  return (
    <>
      <div className={`relative`}>
        <p
          className={`absolute text-xl uppercase font-semibold top-2 left-2 cursor-pointer`}
        >
          MF Platform
        </p>
        <div
          className={`h-screen dark:bg-gray-950 bg-accent w-full flex items-center justify-center`}
        >
          <div
            className={`w-5/12 dark:bg-background h-[500px] px-5 flex flex-col justify-evenly items-center border shadow-lg rounded-3xl`}
          >
            <div className={`space-y-3`}>
              <span className={`flex items-center justify-center`}>
                <IoFingerPrint
                  className={`text-[80px] shadow text-white bg-gradient-to-r from-cyan-500 to-blue-500 border rounded-full p-2`}
                />
              </span>
              <h1 className={`text-center select-none text-2xl font-medium`}>
                Reset Password
              </h1>
            </div>
            {children}
            <div
              className={`flex flex-col items-center justify-between gap-y-2`}
            >
              <Link
                target={"_blank"}
                className={`text-blue-500 flex items-end font-light hover:underline underline-offset-2`}
                href={`/auth/login`}
              >
                Do you have account? <GoArrowUpRight />
              </Link>
              <Link
                className={`text-blue-500 flex items-end font-light hover:underline underline-offset-2`}
                href={`/contact/case/`}
              >
                Apply for account creation
              </Link>
            </div>
          </div>
        </div>
      </div>
    </>
  );
};

export default Layout;
