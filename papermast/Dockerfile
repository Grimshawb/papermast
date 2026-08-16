FROM mcr.microsoft.com/dotnet/sdk:10.0 AS build

WORKDIR /src
COPY papermast/papermast.csproj papermast/dotnet-tools.json ./
RUN dotnet restore papermast.csproj
RUN dotnet tool restore

COPY papermast/ ./
RUN dotnet publish papermast.csproj -c Release -o /out/app --no-restore /p:UseAppHost=false
RUN dotnet ef migrations bundle -o /out/efbundle

FROM mcr.microsoft.com/dotnet/aspnet:10.0 AS runtime

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY --from=build /out/app ./
COPY --from=build /out/efbundle ./efbundle

USER $APP_UID
EXPOSE 8080
ENTRYPOINT ["dotnet", "papermast.dll"]
