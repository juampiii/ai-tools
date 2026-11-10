using AgentGateway.API.Configuration;
using AgentGateway.Application.Configuration;
using AgentGateway.Infrastructure.Configuration;

var builder = WebApplication.CreateBuilder(args);

builder.WebHost.UseUrls("http://localhost:5052");

builder.Services.AddApiServices(builder.Configuration);
builder.Services.AddApplicationServices();
builder.Services.AddInfrastructure(builder.Configuration);

var app = builder.Build();

app.UseApiServices();

app.Run();
