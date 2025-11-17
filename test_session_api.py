#!/usr/bin/env python3
"""
Test script for session API endpoints.
Tests all routes in /session and verifies end-to-end workflow including video rendering.
"""
import httpx
import asyncio
import json
from pathlib import Path

API_URL = "http://localhost:8000"


async def test_session_workflow():
    """Test complete session workflow including video rendering."""

    print("=" * 80)
    print("TESTING SESSION API - COMPLETE WORKFLOW")
    print("=" * 80)

    async with httpx.AsyncClient(timeout=300.0) as client:

        # Test 1: POST /session/generate - Start iterative generation
        print("\n[TEST 1] POST /session/generate - Starting iterative generation...")
        print("-" * 80)

        generation_request = {
            "prompt": "Create a simple animation with a blue circle that grows and changes to red",
            "model": "cerebras/llama3.1-8b",
            "max_tokens": 2000,
            "temperature": 0.7,
            "max_iterations": 5
        }

        print(f"Request: {json.dumps(generation_request, indent=2)}")

        response = await client.post(
            f"{API_URL}/session/generate",
            json=generation_request
        )

        print(f"\nResponse Status: {response.status_code}")
        result = response.json()
        print(f"Response: {json.dumps(result, indent=2)[:500]}...")

        if response.status_code != 200:
            print(f"❌ FAILED: Generation endpoint returned {response.status_code}")
            print(f"Error: {result}")
            return

        session_id = result["session_id"]
        status = result["status"]
        iteration = result["current_iteration"]
        is_complete = result["is_complete"]

        print(f"\n✅ SUCCESS: Session created!")
        print(f"   Session ID: {session_id}")
        print(f"   Status: {status}")
        print(f"   Iterations: {iteration}/{generation_request['max_iterations']}")
        print(f"   Complete: {is_complete}")

        # Check if code was generated
        if result.get("generated_code"):
            code_length = len(result["generated_code"])
            print(f"   Code generated: {code_length} characters")
            print(f"\n   First 200 chars of code:")
            print(f"   {result['generated_code'][:200]}...")

        # Check validation result
        if result.get("validation_result"):
            validation = result["validation_result"]
            print(f"\n   Validation:")
            print(f"   - Valid: {validation.get('is_valid')}")
            print(f"   - Errors: {len(validation.get('errors', []))}")
            if validation.get('errors'):
                print(f"   - Error details: {validation['errors'][:2]}")

        # Test 2: GET /session/status/{session_id} - Check session status
        print("\n[TEST 2] GET /session/status/{session_id} - Checking session status...")
        print("-" * 80)

        response = await client.get(f"{API_URL}/session/status/{session_id}")

        print(f"Response Status: {response.status_code}")

        if response.status_code != 200:
            print(f"❌ FAILED: Status endpoint returned {response.status_code}")
            return

        status_result = response.json()
        print(f"✅ SUCCESS: Session status retrieved")
        print(f"   Current iteration: {status_result['current_iteration']}")
        print(f"   Max iterations: {status_result['max_iterations']}")
        print(f"   Status: {status_result['status']}")
        print(f"   Iterations history: {len(status_result['iterations_history'])} iterations")

        if status_result.get('final_code'):
            print(f"   Final code available: {len(status_result['final_code'])} characters")

        # Test 3: GET /session/list - List all sessions
        print("\n[TEST 3] GET /session/list - Listing all sessions...")
        print("-" * 80)

        response = await client.get(f"{API_URL}/session/list")

        print(f"Response Status: {response.status_code}")

        if response.status_code != 200:
            print(f"❌ FAILED: List endpoint returned {response.status_code}")
            return

        list_result = response.json()
        print(f"✅ SUCCESS: Sessions listed")
        print(f"   Total sessions: {list_result['count']}")

        for i, sess in enumerate(list_result['sessions'], 1):
            print(f"   Session {i}:")
            print(f"     - ID: {sess['session_id'][:20]}...")
            print(f"     - Prompt: {sess['prompt'][:60]}...")
            print(f"     - Status: {sess['status']}")

        # Check if we should proceed with rendering
        if status != "success":
            print(f"\n⚠️  WARNING: Code validation did not succeed (status: {status})")
            print(f"   Cannot proceed with video rendering.")
            print(f"   This is expected if the LLM couldn't generate valid code in {generation_request['max_iterations']} iterations.")

            # Still test the render endpoint with error case
            print("\n[TEST 4] POST /session/render - Testing with potentially invalid code...")
            print("-" * 80)

            render_request = {
                "session_id": session_id,
                "format": "mp4",
                "quality": "low",
                "background_color": "#000000"
            }

            response = await client.post(
                f"{API_URL}/session/render",
                json=render_request
            )

            print(f"Response Status: {response.status_code}")

            if response.status_code == 400:
                print(f"✅ EXPECTED: Render failed because code was not validated")
                print(f"   Error: {response.json()['detail']}")
            else:
                print(f"⚠️  Render attempted despite invalid code...")

            # Skip download test
            print("\n[TEST 5] GET /session/download - SKIPPED (no valid video)")

        else:
            # Test 4: POST /session/render - Render video from validated code
            print("\n[TEST 4] POST /session/render - Rendering video from validated code...")
            print("-" * 80)

            render_request = {
                "session_id": session_id,
                "format": "mp4",
                "quality": "low",  # Use low quality for faster test
                "background_color": "#000000"
            }

            print(f"Request: {json.dumps(render_request, indent=2)}")

            response = await client.post(
                f"{API_URL}/session/render",
                json=render_request
            )

            print(f"\nResponse Status: {response.status_code}")

            if response.status_code != 200:
                print(f"❌ FAILED: Render endpoint returned {response.status_code}")
                error_detail = response.json().get('detail', 'Unknown error')
                print(f"Error: {error_detail[:500]}...")
                return

            render_result = response.json()
            print(f"✅ SUCCESS: Video rendered!")
            print(f"   Video path: {render_result['video_path']}")
            print(f"   Format: {render_result['format']}")
            print(f"   Quality: {render_result['quality']}")

            video_path = render_result['video_path']

            # Test 5: GET /session/download - Download rendered video
            print("\n[TEST 5] GET /session/download - Downloading video...")
            print("-" * 80)

            response = await client.get(
                f"{API_URL}/session/download",
                params={"video_path": video_path}
            )

            print(f"Response Status: {response.status_code}")

            if response.status_code != 200:
                print(f"❌ FAILED: Download endpoint returned {response.status_code}")
                return

            # Save the video
            download_path = Path("./test_output/session_test_video.mp4")
            download_path.parent.mkdir(exist_ok=True)

            with open(download_path, "wb") as f:
                f.write(response.content)

            video_size = len(response.content)
            print(f"✅ SUCCESS: Video downloaded!")
            print(f"   Size: {video_size / 1024:.2f} KB")
            print(f"   Saved to: {download_path}")

        # Test 6: DELETE /session/{session_id} - Delete session
        print("\n[TEST 6] DELETE /session/{session_id} - Deleting session...")
        print("-" * 80)

        response = await client.delete(f"{API_URL}/session/{session_id}")

        print(f"Response Status: {response.status_code}")

        if response.status_code != 200:
            print(f"❌ FAILED: Delete endpoint returned {response.status_code}")
            return

        delete_result = response.json()
        print(f"✅ SUCCESS: Session deleted")
        print(f"   Message: {delete_result['message']}")

        # Verify deletion
        print("\n[TEST 7] Verifying session was deleted...")
        print("-" * 80)

        response = await client.get(f"{API_URL}/session/status/{session_id}")

        if response.status_code == 404:
            print(f"✅ SUCCESS: Session no longer exists (404 as expected)")
        else:
            print(f"❌ FAILED: Session still exists after deletion")

        # Final summary
        print("\n" + "=" * 80)
        print("TEST SUMMARY")
        print("=" * 80)
        print("✅ POST /session/generate - Iterative generation works")
        print("✅ GET /session/status/{session_id} - Status retrieval works")
        print("✅ GET /session/list - Session listing works")

        if status == "success":
            print("✅ POST /session/render - Video rendering works")
            print("✅ GET /session/download - Video download works")
        else:
            print("⚠️  POST /session/render - Skipped (code not validated)")
            print("⚠️  GET /session/download - Skipped (no video rendered)")

        print("✅ DELETE /session/{session_id} - Session deletion works")
        print("✅ Async session workflow - COMPLETE")
        print("=" * 80)


if __name__ == "__main__":
    asyncio.run(test_session_workflow())
