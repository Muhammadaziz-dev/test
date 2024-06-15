import React from "react";
import initTranslations from "@/app/i18n";
import TranslationProvider from "@/prviders/translation.provider";

const i18nNamespaces = ["translation"];

export default async function Layout({ children, params: { locale } }: any) {
  const { resources } = await initTranslations(locale, i18nNamespaces);

  return (
    <TranslationProvider
      locale={locale}
      resources={resources}
      namespaces={i18nNamespaces}
    >
      {children}
    </TranslationProvider>
  );
}
