using AdPorts.AiPortal.Application.Common.Interfaces;
using AdPorts.AiPortal.Application.Projects.Commands.CreateProject;
using AdPorts.AiPortal.Application.Projects.Queries.GetProjects;
using AdPorts.AiPortal.Domain.Entities;
using AdPorts.AiPortal.Infrastructure.Persistence;
using FluentAssertions;
using Microsoft.EntityFrameworkCore;
using NSubstitute;
using Xunit;

namespace AdPorts.AiPortal.Tests.Unit.Application;

public class ProjectHandlerTests
{
    private static PortalDbContext BuildInMemoryContext()
    {
        var opts = new DbContextOptionsBuilder<PortalDbContext>()
            .UseInMemoryDatabase(Guid.NewGuid().ToString())
            .Options;
        return new PortalDbContext(opts);
    }

    [Fact]
    public async Task CreateProject_UniqueSlug_ReturnsId()
    {
        var db = BuildInMemoryContext();
        var user = Substitute.For<ICurrentUser>();
        user.Id.Returns(Guid.NewGuid());

        var handler = new CreateProjectHandler(db, user);
        var id = await handler.Handle(new CreateProjectCommand("orbit-test", "Orbit Test", null, null), default);
        id.Should().NotBe(Guid.Empty);
    }

    [Fact]
    public async Task CreateProject_DuplicateSlug_Throws()
    {
        var db = BuildInMemoryContext();
        var user = Substitute.For<ICurrentUser>();
        user.Id.Returns(Guid.NewGuid());

        var handler = new CreateProjectHandler(db, user);
        await handler.Handle(new CreateProjectCommand("dup", "Dup", null, null), default);

        var act = async () => await handler.Handle(new CreateProjectCommand("dup", "Dup2", null, null), default);
        await act.Should().ThrowAsync<InvalidOperationException>();
    }

    [Fact]
    public async Task GetProjects_FilterByProgram_ReturnsMatchingOnly()
    {
        var db = BuildInMemoryContext();
        db.Add(Project.Create("p1", "P1", "JUL", null, null));
        db.Add(Project.Create("p2", "P2", "PCS", null, null));
        await db.SaveChangesAsync();

        var handler = new GetProjectsQueryHandler(db);
        var result = await handler.Handle(new GetProjectsQuery(Program: "JUL"), default);
        result.Items.Should().HaveCount(1);
        result.Items[0].Slug.Should().Be("p1");
    }
}
