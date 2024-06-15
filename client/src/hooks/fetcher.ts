import useSWR from "swr";
import fetcher from "@/lib/fetcher";

export const useFetch = (url: string) => {
  const { data, error, isLoading, mutate } = useSWR(`${url}`, fetcher);

  return {
    data,
    isLoading,
    isError: error,
    mutate,
  };
};

export default useFetch;
