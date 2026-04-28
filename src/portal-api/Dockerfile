FROM harbor.ai.adports.ae/dotnet/sdk:9.0 AS build
WORKDIR /src
COPY AdPorts.AiPortal.sln .
COPY AdPorts.AiPortal.Api/AdPorts.AiPortal.Api.csproj                         AdPorts.AiPortal.Api/
COPY AdPorts.AiPortal.Application/AdPorts.AiPortal.Application.csproj         AdPorts.AiPortal.Application/
COPY AdPorts.AiPortal.Domain/AdPorts.AiPortal.Domain.csproj                   AdPorts.AiPortal.Domain/
COPY AdPorts.AiPortal.Infrastructure/AdPorts.AiPortal.Infrastructure.csproj   AdPorts.AiPortal.Infrastructure/
COPY AdPorts.AiPortal.Tests/AdPorts.AiPortal.Tests.csproj                     AdPorts.AiPortal.Tests/
RUN dotnet restore

COPY . .
RUN dotnet publish AdPorts.AiPortal.Api/AdPorts.AiPortal.Api.csproj \
    -c Release -o /app/publish --no-restore

FROM harbor.ai.adports.ae/dotnet/aspnet:9.0 AS runtime
WORKDIR /app
EXPOSE 8080
ENV ASPNETCORE_URLS=http://+:8080 \
    ASPNETCORE_ENVIRONMENT=Production
COPY --from=build /app/publish .
ENTRYPOINT ["dotnet", "AdPorts.AiPortal.Api.dll"]
